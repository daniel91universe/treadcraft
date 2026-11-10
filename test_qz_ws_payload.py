import copy
import json
from pathlib import Path
import unittest

from device_capabilities import ProfileCompatibilityError
from qz_ws_payload import build_save_payload
from qz_xml_export import QzXmlExportError, export_workout


def segment(minutes=10, speed=8, incline=1, **fields):
    return dict(name="Run", duration_min=minutes, speed_kmh=speed,
                incline_percent=incline, **fields)


class QzSavePayloadTests(unittest.TestCase):
    def test_timed_segment_with_positive_incline(self):
        payload = build_save_payload({"segments": [segment(incline=2.5)]}, name="Tempo")
        self.assertEqual(json.loads(json.dumps(payload, allow_nan=False)), {
            "msg": "savetrainingprogram",
            "content": {"name": "Tempo", "list": [{
                "duration": "00:10:00", "speed": 8, "inclination": 2.5,
                "forcespeed": True, "zoneHR": 0,
            }]},
        })

    def test_distance_in_meters_and_kilometers(self):
        for unit, value in (("m", 3000.125), ("km", 3.000125)):
            with self.subTest(unit=unit):
                workout = {"segments": [segment(
                    measure_mode="Distance", distance_unit=unit, measure_value=value,
                )]}
                row, = build_save_payload(workout, name="Distance")["content"]["list"]
                self.assertIsInstance(row["distance"], (int, float))
                self.assertEqual(row["distance"], 3.000125)
                self.assertEqual(row["duration"], "00:22:30")

    def test_multiple_blocks_keep_repeats_and_recoveries_in_order(self):
        workout = {"blocks": [
            {"name": "First", "repetitions": 2,
             "segments": [segment(3, 12), segment(1, 6)]},
            {"name": "Second", "repetitions": 3,
             "segments": [segment(2, 14), segment(1, 8)]},
        ]}
        rows = build_save_payload(workout, name="Intervals")["content"]["list"]
        self.assertEqual([(r["duration"], r["speed"]) for r in rows],
                         [("00:03:00", 12), ("00:01:00", 6)] * 2
                         + [("00:02:00", 14), ("00:01:00", 8)] * 3)

    def test_invalid_workouts_keep_exporter_validation(self):
        for workout in ({}, {"segments": [segment(speed=0)]},
                        {"segments": [segment(incline=-2)]}):
            with self.subTest(workout=workout), self.assertRaises(ProfileCompatibilityError):
                build_save_payload(workout, name="Invalid")

    def test_blank_program_name_is_rejected(self):
        with self.assertRaisesRegex(QzXmlExportError, "program name"):
            build_save_payload({"segments": [segment()]}, name="  ")

    def test_missing_distance_duration_blocks_only_websocket_payload(self):
        for meters in (0.1, 200000):
            with self.subTest(meters=meters):
                workout = {"segments": [segment(
                    measure_mode="Distance", distance_unit="m", measure_value=meters,
                )]}
                self.assertIn("preview_duration_unavailable",
                              {d.code for d in export_workout(workout).diagnostics})
                with self.assertRaisesRegex(QzXmlExportError, "row 1 needs a duration"):
                    build_save_payload(workout, name="Distance")

    def test_sample_3x3000_keeps_eight_rows_and_original_json(self):
        path = Path(__file__).resolve().parent / "examples" / "3x3000mt.json"
        original = path.read_bytes()
        workout = json.loads(original)
        before = copy.deepcopy(workout)
        rows = build_save_payload(workout, name="3x3000 test")["content"]["list"]
        self.assertEqual([(r.get("distance"), r["duration"], r["speed"]) for r in rows],
                         [(None, "00:10:00", 10)]
                         + [(3, "00:12:51", 14), (None, "00:03:00", 10)] * 3
                         + [(None, "00:05:00", 10)])
        self.assertEqual(workout, before)
        self.assertEqual(path.read_bytes(), original)
