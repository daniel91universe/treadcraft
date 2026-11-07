"""Regression tests; run with python -B -m unittest -v."""

import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from workout_data import (
    calculate_totals, normalize_block_values, normalize_segment, normalize_workout,
)
from app import TreadmillApp


ROOT = Path(__file__).resolve().parent


def segment(**changes):
    data = {"name": "Easy", "duration_min": 10, "speed_kmh": 8,
            "incline_percent": 1}
    data.update(changes)
    return data


def workout(data=None):
    return {"format_version": 4, "workout_name": "Test", "blocks": [
        {"type": "segment", "segment": segment() if data is None else data}
    ]}


class CompatibilityTests(unittest.TestCase):
    def test_v4_fixture_is_unchanged_after_normalization(self):
        original = json.loads((ROOT / "examples/3x3000mt.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(original)
        normalized = normalize_workout(original)
        self.assertEqual(normalized, original)
        self.assertEqual(original, before)
        self.assertEqual(calculate_totals(normalized["blocks"]), (62.5713, 13.0))

    def test_legacy_fixture_keeps_order_values_and_totals(self):
        original = json.loads((ROOT / "tests/fixtures/legacy-workout.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(original)
        normalized = normalize_workout(original)
        block = normalized["blocks"][0]
        self.assertEqual(block["type"], "block")
        self.assertEqual(block["repetitions"], 1)
        self.assertEqual([s["name"] for s in block["segments"]],
                         [s["name"] for s in original["segments"]])
        for old, new in zip(original["segments"], block["segments"]):
            for key in ("name", "duration_min", "speed_kmh", "incline_percent"):
                self.assertEqual(old[key], new[key])
            self.assertEqual(new["measure_mode"], "Time")
        self.assertEqual(normalized["total_duration_min"], 20)
        self.assertEqual(normalized["estimated_distance_km"], 2.25)
        self.assertEqual(original, before)

    def test_example_matches_original(self):
        path = ROOT / "examples/3x3000mt.json"
        data = path.read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(data).hexdigest().upper(),
                         "EAF2A1AE6321DC79AD6066B81A9C7BFAC2ED1C7005C6F84096CF35814CBC5510")


    def test_supported_versions_and_untyped_historical_blocks(self):
        for version in (None, 1, 2, 3, 4):
            value = {"blocks": [{"name": "Old", "repetitions": "2",
                                 "segments": [segment()]}]}
            if version is not None:
                value["format_version"] = version
            with self.subTest(version=version):
                normalized = normalize_workout(value)
                self.assertEqual(normalized["blocks"][0]["type"], "block")
                self.assertEqual(normalized["total_duration_min"], 20)

    def test_save_load_roundtrip_is_stable_for_both_fixtures(self):
        for name in ("examples/3x3000mt.json", "tests/fixtures/legacy-workout.json"):
            with self.subTest(name=name):
                first = normalize_workout(json.loads((ROOT / name).read_text(encoding="utf-8")))
                serialized = json.dumps(first, allow_nan=False)
                self.assertEqual(normalize_workout(json.loads(serialized)), first)

    def test_distance_in_meters_and_fallback_in_km(self):
        data = segment(measure_mode="Distance", measure_value=3000,
                       distance_unit="m", speed_kmh=12)
        normalized = normalize_segment(data)
        self.assertEqual(normalized["duration_min"], 15)
        self.assertEqual(normalized["estimated_distance_km"], 3)
        del data["measure_value"]
        data["estimated_distance_km"] = 3
        self.assertEqual(normalize_segment(data), normalized)

    def test_numeric_strings_and_boundary_values(self):
        for speed, incline in (("0.1", "-3"), ("20", "12")):
            normalized = normalize_segment(segment(speed_kmh=speed, incline_percent=incline))
            self.assertEqual(normalized["speed_kmh"], float(speed))
            self.assertEqual(normalized["incline_percent"], float(incline))
        for value in (1, 100, "1", "100", 2.0):
            self.assertEqual(normalize_block_values("Block", value)["repetitions"], int(value))

    def test_stale_finite_cached_totals_are_recalculated(self):
        data = workout(segment(estimated_distance_km=99))
        data.update(total_duration_min=999, estimated_distance_km=999)
        result = normalize_workout(data)
        self.assertEqual(result["total_duration_min"], 10)
        self.assertEqual(result["estimated_distance_km"], 1.3333)

    def test_empty_blocks_remain_readable(self):
        result = normalize_workout({"blocks": [{"name": "Empty", "repetitions": 1,
                                               "segments": []}]})
        self.assertEqual(result["total_duration_min"], 0)


class InvalidDataTests(unittest.TestCase):
    def test_non_finite_and_boolean_numeric_fields(self):
        for key in ("speed_kmh", "incline_percent", "duration_min",
                    "estimated_distance_km", "measure_value"):
            for value in (float("nan"), float("inf"), -float("inf"), "NaN", "Infinity", True):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError):
                        normalize_segment(segment(**{key: value}))

    def test_invalid_repetitions_are_never_truncated(self):
        for value in (0, 101, 1.5, "1.5", True, None, [], float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_workout({"blocks": [{"name": "Block", "repetitions": value,
                                                   "segments": [segment()]}]})

    def test_invalid_versions(self):
        for version in (0, 5, -1, "4", 4.0, True, None, [], float("inf")):
            with self.subTest(version=version):
                data = workout()
                data["format_version"] = version
                with self.assertRaisesRegex(ValueError, "format_version"):
                    normalize_workout(data)

    def test_wrong_json_shapes_have_validation_errors(self):
        for value in (None, [], "text", 5, {"blocks": None}, {"blocks": [None]},
                      {"blocks": [5]}, {"blocks": [{"type": "segment", "segment": []}]},
                      {"blocks": [{"name": "X", "repetitions": 1, "segments": {}}]},
                      {"segments": []}, {"segments": [None]},
                      {"blocks": [], "segments": [segment()]},
                      {"blocks": [], "workout_name": None}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_workout(value)

    def test_missing_required_fields(self):
        for key in ("name", "duration_min", "speed_kmh", "incline_percent"):
            with self.subTest(key=key):
                data = segment()
                del data[key]
                with self.assertRaisesRegex(ValueError, "missing"):
                    normalize_workout(workout(data))

    def test_unknown_fields_and_modes_do_not_silently_disappear(self):
        cases = [workout(segment(fanspeed=2)), workout(segment(measure_mode="Minutes")),
                 workout(segment(measure_mode=None)), workout(segment(distance_unit="mi"))]
        data = workout()
        data["metadata"] = {"note": "must not be silently deleted"}
        cases.append(data)
        data = workout()
        data["blocks"][0]["type"] = "future_type"
        cases.append(data)
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    normalize_workout(data)

    def test_bounds_names_and_tiny_values(self):
        for changes in ({"speed_kmh": 0}, {"speed_kmh": 20.1}, {"incline_percent": -3.1},
                        {"incline_percent": 12.1}, {"name": None}, {"name": " "},
                        {"duration_min": 0}, {"duration_min": 1e-10},
                        {"measure_mode": "Distance", "measure_value": 0}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    normalize_segment(segment(**changes))

    def test_derived_and_total_overflow_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_segment(segment(duration_min=1e308, speed_kmh=20))
        data = {"blocks": [{"name": "Large", "repetitions": 100,
                            "segments": [segment(duration_min=1e308, speed_kmh=0.001)]}]}
        with self.assertRaisesRegex(ValueError, "Total duration"):
            normalize_workout(data)

    def test_nested_blocks_are_rejected(self):
        data = {"blocks": [{"name": "Outer", "repetitions": 1,
                            "segments": [{"type": "block", "name": "Nested",
                                          "repetitions": 2, "segments": [segment()]}]}]}
        with self.assertRaises(ValueError):
            normalize_workout(data)


class EditorIntegrationTests(unittest.TestCase):
    def make_editor(self):
        editor = TreadmillApp.__new__(TreadmillApp)
        editor.blocks = normalize_workout(workout())["blocks"]
        editor.workout_name = Mock()
        editor.workout_name.get.return_value = "Existing"
        for method in ("reset_block_editor", "reset_segment_editor", "refresh_tree", "update_summary"):
            setattr(editor, method, Mock())
        return editor

    def test_failed_import_preserves_name_blocks_and_ui_state(self):
        editor = self.make_editor()
        original = editor.blocks
        for data in ({"blocks": [None]}, workout(segment(speed_kmh="NaN")),
                     dict(workout(), format_version=5)):
            with self.subTest(data=data):
                with patch("app.filedialog.askopenfilename", return_value="invalid.json"), \
                        patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(data))), \
                        patch("app.messagebox.showerror") as error:
                    editor.open_workout()
                error.assert_called_once()
                self.assertIs(editor.blocks, original)
                editor.workout_name.set.assert_not_called()
                editor.refresh_tree.assert_not_called()
                editor.reset_segment_editor.assert_not_called()

    def test_legacy_import_commits_only_validated_data(self):
        editor = self.make_editor()
        with patch("app.filedialog.askopenfilename", return_value=str(ROOT / "tests/fixtures/legacy-workout.json")), \
                patch("app.messagebox.showinfo"):
            editor.open_workout()
        self.assertEqual(editor.blocks[0]["type"], "block")
        self.assertEqual(len(editor.blocks[0]["segments"]), 3)
        editor.refresh_tree.assert_called_once()

    def test_ui_input_uses_the_same_validation(self):
        editor = self.make_editor()
        for name, value in (("segment_name", "Easy"), ("measure_mode", "Time"),
                            ("measure_value", "10"), ("distance_unit", "km"),
                            ("speed", "NaN"), ("incline", "1")):
            field = Mock()
            field.get.return_value = value
            setattr(editor, name, field)
        with patch("app.messagebox.showerror") as error:
            self.assertIsNone(editor.get_segment_values())
        error.assert_called_once()
        editor.speed.get.return_value = "8"
        self.assertEqual(editor.get_segment_values(), normalize_segment(segment()))

    def test_invalid_save_never_opens_destination(self):
        editor = self.make_editor()
        bad_segment = normalize_segment(segment())
        bad_segment["speed_kmh"] = float("nan")
        for blocks in ([{"type": "segment", "segment": bad_segment}], [None]):
            with self.subTest(blocks=blocks):
                editor.blocks = blocks
                with patch("app.messagebox.showerror") as error, \
                        patch("app.filedialog.asksaveasfilename") as dialog, \
                        patch("builtins.open") as opened:
                    editor.save_workout()
                error.assert_called_once()
                dialog.assert_not_called()
                opened.assert_not_called()

    def test_malformed_json_preserves_existing_workout(self):
        editor = self.make_editor()
        original = editor.blocks
        with patch("app.filedialog.askopenfilename", return_value="invalid.json"), \
                patch("builtins.open", unittest.mock.mock_open(read_data='{"blocks":')), \
                patch("app.messagebox.showerror") as error:
            editor.open_workout()
        error.assert_called_once()
        self.assertIs(editor.blocks, original)
        editor.workout_name.set.assert_not_called()

    def test_empty_workout_save_keeps_existing_warning(self):
        editor = self.make_editor()
        editor.blocks = []
        with patch("app.messagebox.showwarning") as warning, \
                patch("app.filedialog.asksaveasfilename") as dialog:
            editor.save_workout()
        warning.assert_called_once()
        dialog.assert_not_called()

    def test_saved_json_uses_v4_and_can_be_reopened(self):
        editor = self.make_editor()
        destination = unittest.mock.mock_open()
        with patch("app.filedialog.asksaveasfilename", return_value="output.json"), \
                patch("builtins.open", destination), patch("app.messagebox.showinfo"):
            editor.save_workout()
        text = destination().write.call_args.args[0]
        data = json.loads(text)
        self.assertEqual(data["format_version"], 4)
        self.assertEqual(normalize_workout(data), data)

    def test_python_sources_parse_without_bytecode_files(self):
        for name in ("app.py", "workout_data.py", "test_workout_data.py"):
            ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)


if __name__ == "__main__":
    unittest.main()
