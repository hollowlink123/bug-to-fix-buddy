import json
import tempfile
import unittest
from pathlib import Path

from bug_report import create_report, load_report, save_report


class BugReportTests(unittest.TestCase):
    def test_create_report_has_required_fields_and_unique_id(self):
        first = create_report("The app crashes on launch")
        second = create_report("The app crashes on launch")

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["description"], "The app crashes on launch")
        self.assertTrue(first["created_at"])
        self.assertEqual(first["status"], "received")

    def test_empty_report_is_rejected(self):
        for description in ("", "  ", "\n\t"):
            with self.subTest(description=description):
                with self.assertRaisesRegex(ValueError, "cannot be empty"):
                    create_report(description)

    def test_save_and_load_report(self):
        report = create_report("A button does not respond")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = save_report(report, temp_dir)
            self.assertEqual(path.name, f"{report['id']}.json")
            self.assertEqual(load_report(path), report)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), report)


if __name__ == "__main__":
    unittest.main()
