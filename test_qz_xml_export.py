import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from device_capabilities import ProfileCompatibilityError
from qz_xml_export import MAX_ROWS, QzXmlExportError, export_workout


ROOT = Path(__file__).resolve().parent


def segment(minutes=10, speed=8, incline=1, **fields):
    return dict(name="Easy", duration_min=minutes, speed_kmh=speed,
                incline_percent=incline, **fields)


class ExportTests(unittest.TestCase):
    def rows(self, result):
        root = ET.fromstring(result.xml.encode("utf-8"))
        self.assertEqual(root.tag, "rows")
        self.assertEqual(len(root), result.row_count)
        for row in root:
            self.assertEqual(row.tag, "row")
            self.assertEqual(len(row), 0)
            end = set(row.attrib) & {"duration", "distance"}
            self.assertEqual(len(end), 1)
            self.assertEqual(set(row.attrib) - end,
                             {"speed", "inclination", "forcespeed", "zonehr"})
            self.assertEqual(row.get("forcespeed"), "1")
            self.assertEqual(row.get("zonehr"), "0")
            self.assertGreater(float(row.get("speed")), 0)
            self.assertGreaterEqual(float(row.get("inclination")), 0)
            if "duration" in end:
                self.assertRegex(row.get("duration"), r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$")
                self.assertNotEqual(row.get("duration"), "00:00:00")
            else:
                self.assertGreater(float(row.get("distance")), 0)
        return list(root)

    def test_easy_run(self):
        result = export_workout({"segments": [segment()]})
        row, = self.rows(result)
        self.assertEqual(row.attrib, dict(duration="00:10:00", speed="8",
                         inclination="1", forcespeed="1", zonehr="0"))
        self.assertEqual(result.timed_seconds, 600)
        self.assertIn("hardware_unverified", {d.code for d in result.diagnostics})

    def test_intervals(self):
        result = export_workout({"blocks": [{"name": "Intervals", "repetitions": 6,
                                            "segments": [segment(3, 12), segment(2, 6)]}]})
        self.assertEqual([(r.get("duration"), r.get("speed")) for r in self.rows(result)],
                         [("00:03:00", "12"), ("00:02:00", "6")] * 6)
        self.assertEqual(result.timed_seconds, 1800)

    def test_original_3x3000(self):
        path = ROOT / "3x3000mt.json"
        original = path.read_bytes()
        data = json.loads(original)
        before = copy.deepcopy(data)
        rows = self.rows(export_workout(data))
        self.assertEqual([(r.get("distance"), r.get("duration")) for r in rows],
                         [(None, "00:10:00")] + [("3", None), (None, "00:03:00")] * 3
                         + [(None, "00:05:00")])
        self.assertEqual([r.get("speed") for r in rows], ["10"] + ["14", "10"] * 3 + ["10"])
        self.assertEqual(data, before)
        self.assertEqual(path.read_bytes(), original)

    def test_legacy_fixture(self):
        result = export_workout(json.loads((ROOT / "Allenamento_test.json").read_bytes()))
        self.assertEqual([r.get("speed") for r in self.rows(result)], ["6", "10", "5"])
        self.assertEqual(result.timed_seconds, 1200)

    def test_meters_and_author_distance_precision(self):
        for meters, expected in [(3000, "3"), (3000.1234, "3.0001234")]:
            with self.subTest(meters=meters):
                result = export_workout({"segments": [segment(
                    measure_mode="Distance", distance_unit="m", measure_value=meters)]})
                row, = self.rows(result)
                self.assertEqual(row.get("distance"), expected)
                self.assertEqual(result.timed_seconds, 0)

    def test_decline_has_segment_name_and_path(self):
        with self.assertRaises(ProfileCompatibilityError) as caught:
            export_workout({"segments": [segment(incline=-2)]})
        issue = next(d for d in caught.exception.report.diagnostics
                     if d.code == "decline_unavailable")
        self.assertIn("Easy", issue.message)
        self.assertEqual(issue.path, "blocks[0].segments[0]")

    def test_fractional_seconds_report_adjustment_across_repetitions(self):
        result = export_workout({"blocks": [{"name": "Short", "repetitions": 3,
                                            "segments": [segment(0.025)]}]})
        self.assertEqual([r.get("duration") for r in self.rows(result)], ["00:00:02"] * 3)
        self.assertEqual(result.timed_seconds, 6)
        self.assertEqual(result.duration_adjustment_seconds, Decimal("1.5"))
        self.assertIn("duration_rounded", {d.code for d in result.diagnostics})

    def test_duration_boundaries(self):
        for minutes, expected in [(0.01, "00:00:01"), (1439.983333333333, "23:59:59")]:
            with self.subTest(minutes=minutes):
                row, = self.rows(export_workout({"segments": [segment(minutes)]}))
                self.assertEqual(row.get("duration"), expected)
        for minutes in (0.005, 1439.999, 1440, 1e100):
            with self.subTest(minutes=minutes):
                with self.assertRaisesRegex(QzXmlExportError, "Easy.*outside"):
                    export_workout({"segments": [segment(minutes)]})

    def test_special_author_names_do_not_enter_qz_markup(self):
        data = {"workout_name": "Corsa & <salita> é", "segments": [segment()]}
        data["segments"][0]["name"] = 'Corsa & <salita> "é"'
        result = export_workout(data)
        self.rows(result)
        self.assertNotIn("Corsa", result.xml)
        self.assertEqual(data["segments"][0]["name"], 'Corsa & <salita> "é"')

    def test_row_budget_before_serialization(self):
        block = {"name": "Large", "repetitions": 100, "segments": [segment()] * 100}
        self.assertEqual(export_workout({"blocks": [block]}).row_count, MAX_ROWS)
        block["segments"].append(segment())
        with patch("qz_xml_export.ET.Element") as create:
            with self.assertRaisesRegex(QzXmlExportError, "Maximum"):
                export_workout({"blocks": [block]})
        create.assert_not_called()

    def test_invalid_inputs(self):
        missing_duration = segment()
        del missing_duration["duration_min"]
        for data in (None, "{bad JSON", {"format_version": 5, "segments": [segment()]},
                     {"blocks": []}, {"segments": [segment(0)]},
                     {"segments": [missing_duration]},
                     {"segments": [segment(measure_mode="Distance")]},
                     {"segments": [segment(speed=float("inf"))]},
                     {"segments": [segment(measure_mode="Distance", measure_value="NaN")]},
                     {"segments": [segment(fanspeed=1)]}):
            with self.subTest(data=data):
                with self.assertRaises(ProfileCompatibilityError):
                    export_workout(data)

    def test_serialization_failure(self):
        with patch("qz_xml_export.ET.tostring", side_effect=TypeError("serialization failed")):
            with self.assertRaisesRegex(QzXmlExportError, "Could not serialize"):
                export_workout({"segments": [segment()]})
