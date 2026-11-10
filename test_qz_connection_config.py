import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from qz_connection_config import load_qz_endpoint, save_qz_endpoint


class QzConnectionConfigTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, {"LOCALAPPDATA": directory}))
        self.path = Path(directory) / "TreadCraft" / "qz_connection.json"

    def test_save_and_replace_persisted_endpoint(self):
        self.assertIsNone(load_qz_endpoint())
        save_qz_endpoint("http://192.168.1.12:41373/floating/floating.htm")
        self.assertEqual(load_qz_endpoint(), "ws://192.168.1.12:41373/")
        save_qz_endpoint("192.168.1.12:41157")
        self.assertEqual(load_qz_endpoint(), "ws://192.168.1.12:41157/")
        self.assertEqual(json.loads(self.path.read_text()), {
            "endpoint": "ws://192.168.1.12:41157/",
        })
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_corrupt_and_non_local_settings_fall_back_to_manual_entry(self):
        self.path.parent.mkdir()
        for content in ("{", "[]", '{"endpoint":123}', '{"endpoint":"ws://8.8.8.8:53/"}'):
            with self.subTest(content=content):
                self.path.write_text(content)
                self.assertIsNone(load_qz_endpoint())
