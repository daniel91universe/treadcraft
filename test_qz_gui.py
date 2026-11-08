import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from app import TreadmillApp, qz_preview, write_qz_xml
from qz_xml_export import export_workout


class ExportGuiTests(unittest.TestCase):
    def setUp(self):
        self.app = TreadmillApp.__new__(TreadmillApp)
        self.app.root = Mock()
        self.app.workout_name = Mock()
        self.workout_path = Path(__file__).parent / "examples" / "3x3000mt.json"
        self.original = self.workout_path.read_bytes()
        self.workout = json.loads(self.original)
        self.app.workout_name.get.return_value = self.workout["workout_name"]
        self.app.blocks = copy.deepcopy(self.workout["blocks"])
        folder = self.enterContext(TemporaryDirectory())
        self.path = Path(folder) / "workout.xml"
        self.dialog = self.enterContext(patch("app.filedialog.asksaveasfilename",
                                              return_value=str(self.path)))
        self.preview = self.app.confirm_qz_preview = Mock(return_value=True)
        self.confirm = self.enterContext(patch("app.messagebox.askyesno", return_value=False))
        self.error = self.enterContext(patch("app.messagebox.showerror"))

    def test_export_matches_mapping_and_preview_preserves_workout(self):
        self.app.export_qz_xml()
        expected = export_workout(self.workout)
        self.assertEqual(self.path.read_bytes(), expected.xml.encode("utf-8"))
        rows = ET.parse(self.path).getroot()
        self.assertEqual(len(rows), 8)
        self.assertEqual([(r.get("distance"), r.get("duration")) for r in rows if r.get("distance")],
                         [("3", "00:12:51")] * 3)
        self.assertEqual(self.app.blocks, self.workout["blocks"])
        self.assertEqual(self.workout_path.read_bytes(), self.original)

    def test_preview_separates_summary_estimates_and_diagnostics(self):
        summary, details = qz_preview(export_workout(self.workout))
        for value in ("XML rows: 8", "Timed segments: 5", "24m 00s",
                      "Distance segments: 3", "38m 33s", "3 of 3"):
            self.assertIn(value, "\n".join(summary))
        self.assertFalse(details["Blocking errors"])
        self.assertIn("hardware behavior", "\n".join(details["Warnings"]))
        self.assertIn("estimates", "\n".join(details["Information"]))

    def test_cancel_preview(self):
        self.preview.return_value = False
        self.app.export_qz_xml()
        self.dialog.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_cancel_destination(self):
        self.dialog.return_value = ""
        self.app.export_qz_xml()
        self.assertFalse(self.path.exists())

    def test_existing_file_requires_confirmation(self):
        self.path.write_bytes(b"previous")
        self.app.export_qz_xml()
        self.confirm.assert_called_once()
        self.assertEqual(self.path.read_bytes(), b"previous")
        self.confirm.return_value = True
        self.app.export_qz_xml()
        self.assertEqual(ET.parse(self.path).getroot().tag, "rows")

    def test_decline_blocks_export(self):
        self.app.blocks[0]["segment"]["incline_percent"] = -2
        self.app.export_qz_xml()
        self.assertIn("Warm-up", self.error.call_args.args[1])
        self.preview.assert_not_called()
        self.dialog.assert_not_called()

    def test_write_failure_leaves_existing_file_and_cleans_temporary(self):
        self.path.write_bytes(b"previous")
        self.confirm.return_value = True
        with patch("app.os.replace", side_effect=PermissionError("Access denied")):
            self.app.export_qz_xml()
        self.assertIn("Access denied", self.error.call_args.args[1])
        self.assertEqual(self.path.read_bytes(), b"previous")
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_new_file_created_by_another_writer_is_preserved(self):
        self.path.write_bytes(b"another writer")
        with self.assertRaises(FileExistsError):
            write_qz_xml(self.path, "<rows/>", overwrite=False)
        self.assertEqual(self.path.read_bytes(), b"another writer")
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_json_destination_is_rejected(self):
        self.dialog.return_value = str(self.workout_path)
        self.app.export_qz_xml()
        self.error.assert_called_once()
        self.confirm.assert_not_called()
        self.assertEqual(self.workout_path.read_bytes(), self.original)
