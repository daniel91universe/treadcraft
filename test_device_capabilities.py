"""Software compatibility checks are separate from hardware verification."""

import copy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, mock_open, patch

from app import TreadmillApp
from device_capabilities import (
    COMMERCIAL_LE, Evidence, ProfileCompatibilityError, assess_workout,
    require_exportable,
)
from workout_data import normalize_workout


ROOT = Path(__file__).resolve().parent


def workout(incline=0, speed=8, repeated=False):
    segment = {"name": "Trail", "duration_min": 3, "speed_kmh": speed,
               "incline_percent": incline}
    entry = ({"type": "block", "name": "Repeated", "repetitions": 6,
              "segments": [segment]} if repeated else
             {"type": "segment", "segment": segment})
    return {"workout_name": "Test", "blocks": [entry]}


def codes(report):
    return {issue.code for issue in report.diagnostics}


class ProfileTests(unittest.TestCase):
    def test_limits_and_steps_are_not_hardware_certified(self):
        self.assertFalse(COMMERCIAL_LE.identification_verified)
        for limit, value in ((COMMERCIAL_LE.speed_max, 20),
                             (COMMERCIAL_LE.incline_min, -3),
                             (COMMERCIAL_LE.incline_max, 12)):
            self.assertEqual(limit.value, value)
            self.assertEqual(limit.evidence, Evidence.PRELIMINARY)
        for limit in (COMMERCIAL_LE.speed_min, COMMERCIAL_LE.speed_step,
                      COMMERCIAL_LE.incline_step):
            self.assertIsNone(limit.value)
            self.assertEqual(limit.evidence, Evidence.UNKNOWN)

    def test_driver_ranges_are_separate_from_project_bounds(self):
        self.assertEqual(COMMERCIAL_LE.driver_speed_max.value, 22)
        self.assertEqual(COMMERCIAL_LE.driver_incline_max.value, 15)
        self.assertEqual(COMMERCIAL_LE.driver_speed_step.value, 0.1)
        self.assertEqual(COMMERCIAL_LE.driver_speed_step.evidence, Evidence.SOURCE_CONFIRMED)
        self.assertIsNone(COMMERCIAL_LE.speed_step.value)
        self.assertTrue(assess_workout(workout(speed=21)).has_blockers)
        self.assertTrue(assess_workout(workout(incline=13)).has_blockers)

    def test_capabilities_distinguish_source_from_hardware(self):
        for key in ("speed", "incline", "heart_rate", "telemetry"):
            cap = COMMERCIAL_LE.capability(key)
            self.assertEqual(cap.qz_evidence, Evidence.SOURCE_CONFIRMED)
            self.assertEqual(cap.hardware_evidence, Evidence.HARDWARE_REQUIRED)
            self.assertTrue(cap.references)
        for key in ("decline", "fan", "stop", "pause"):
            self.assertEqual(COMMERCIAL_LE.capability(key).qz_evidence, Evidence.UNSUPPORTED)
        self.assertEqual(COMMERCIAL_LE.capability("start").qz_evidence, Evidence.UNKNOWN)

    def test_profile_is_immutable_and_pinned(self):
        with self.assertRaises(FrozenInstanceError):
            COMMERCIAL_LE.speed_max.value = 22
        self.assertEqual(COMMERCIAL_LE.qz_commit,
                         "89ebf525e87fe3f334c437e656417e1f818b9e27")

    def test_normal_workout_has_warnings_not_hardware_approval(self):
        for incline in (0, 1, 12):
            with self.subTest(incline=incline):
                report = assess_workout(workout(incline))
                self.assertFalse(report.has_blockers)
                self.assertIn("preliminary_limits", codes(report))
                self.assertIn("hardware_unverified", codes(report))
                self.assertIn("stop_limitation", codes(report))
                self.assertIn("fan_limitation", codes(report))
                self.assertIn("not a hardware compatibility certification", report.text())

    def test_decline_is_blocked_with_path_without_changing_data(self):
        for repeated in (False, True):
            data = workout(-2, repeated=repeated)
            before = copy.deepcopy(data)
            report = assess_workout(data)
            self.assertTrue(report.has_blockers)
            issue = next(d for d in report.diagnostics if d.code == "decline_unavailable")
            self.assertEqual(issue.path, "blocks[0].segments[0]" if repeated
                             else "blocks[0].segment")
            self.assertIn("negative incline with zero", issue.message)
            self.assertEqual(data, before)
            # Compatibility restrictions do not prevent author JSON persistence.
            normalized = normalize_workout(data)
            self.assertEqual(normalize_workout(json.loads(json.dumps(normalized))), normalized)

    def test_optional_requirements_fail_closed(self):
        for feature in ("fan", "stop", "start", "pause", "decline", "unknown"):
            with self.subTest(feature=feature):
                with self.assertRaises(ProfileCompatibilityError):
                    require_exportable(workout(), required_features=(feature,))

    def test_valid_gate_still_returns_hardware_warnings(self):
        report = require_exportable(workout())
        self.assertIn("hardware_unverified", codes(report))
        self.assertFalse(report.has_blockers)

    def test_unknown_physical_steps_do_not_quantize_author_values(self):
        data = workout(incline=1.25, speed=8.05)
        before = copy.deepcopy(data)
        self.assertFalse(assess_workout(data).has_blockers)
        self.assertEqual(data, before)
        self.assertIsNone(COMMERCIAL_LE.speed_step.value)
        self.assertIsNone(COMMERCIAL_LE.incline_step.value)

    def test_profile_bounds_are_applied_without_clamping(self):
        profile = replace(COMMERCIAL_LE, speed_max=replace(COMMERCIAL_LE.speed_max, value=7))
        data = workout(speed=8)
        original = copy.deepcopy(data)
        report = assess_workout(data, profile)
        self.assertIn("profile_limit", codes(report))
        self.assertEqual(data, original)
        self.assertIn("to 7 km/h", report.text())

    def test_existing_json_files_check_without_mutation(self):
        for name in ("3x3000mt.json", "Allenamento_test.json"):
            path = ROOT / name
            before = path.read_bytes()
            data = json.loads(before)
            original = copy.deepcopy(data)
            report = assess_workout(data)
            self.assertFalse(report.has_blockers)
            self.assertEqual(data, original)
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_and_empty_workouts_block_the_gate(self):
        for data in (None, {"blocks": [None]}, workout(speed=float("nan")), {"blocks": []}):
            with self.subTest(data=data):
                self.assertTrue(assess_workout(data).has_blockers)


class EditorProfileTests(unittest.TestCase):
    def make_editor(self, incline):
        editor = TreadmillApp.__new__(TreadmillApp)
        editor.blocks = normalize_workout(workout(incline))["blocks"]
        editor.workout_name = Mock()
        editor.workout_name.get.return_value = "Test"
        return editor

    def test_check_shows_error_or_warning_without_writing_or_mutation(self):
        for incline, blocked in ((0, False), (-2, True)):
            with self.subTest(incline=incline):
                editor = self.make_editor(incline)
                original = copy.deepcopy(editor.blocks)
                reference = editor.blocks
                with patch("app.messagebox.showerror") as error, \
                        patch("app.messagebox.showwarning") as warning, \
                        patch("builtins.open") as opened:
                    report = editor.check_commercial_le()
                self.assertEqual(report.has_blockers, blocked)
                self.assertEqual(error.call_count, int(blocked))
                self.assertEqual(warning.call_count, int(not blocked))
                self.assertIs(editor.blocks, reference)
                self.assertEqual(editor.blocks, original)
                editor.workout_name.set.assert_not_called()
                opened.assert_not_called()

    def test_decline_check_does_not_block_json_save_or_add_profile_fields(self):
        editor = self.make_editor(-2)
        with patch("app.messagebox.showerror"):
            self.assertTrue(editor.check_commercial_le().has_blockers)
        destination = mock_open()
        with patch("app.filedialog.asksaveasfilename", return_value="output.json"), \
                patch("builtins.open", destination), patch("app.messagebox.showinfo"):
            editor.save_workout()
        saved = json.loads(destination().write.call_args.args[0])
        self.assertEqual(saved["format_version"], 4)
        self.assertEqual(saved["blocks"][0]["segment"]["incline_percent"], -2)
        self.assertEqual(set(saved), {"format_version", "workout_name", "blocks",
                                      "total_duration_min", "estimated_distance_km"})


if __name__ == "__main__":
    unittest.main()
