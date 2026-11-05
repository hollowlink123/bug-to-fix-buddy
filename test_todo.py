import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_SCRIPT = Path(__file__).with_name("todo.py")


class TodoPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)
        self.script = self.project_dir / "todo.py"
        self.tasks_file = self.project_dir / "tasks.json"
        shutil.copy2(SOURCE_SCRIPT, self.script)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8:replace"
        return subprocess.run(
            [sys.executable, str(self.script), *args],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )

    def test_first_run_lists_examples_without_creating_save(self):
        result = self.run_cli("list")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1. Write the project README", result.stdout)
        self.assertIn("2. Review the demo bug report", result.stdout)
        self.assertFalse(self.tasks_file.exists())

    def test_completion_persists_between_invocations(self):
        complete_result = self.run_cli("done", "2")
        list_result = self.run_cli("list")

        self.assertEqual(complete_result.returncode, 0, complete_result.stderr)
        self.assertEqual(list_result.returncode, 0, list_result.stderr)
        self.assertIn("2. Review the demo bug report — done", list_result.stdout)

    def test_demo_persists_task_one_and_leaves_task_two_unchanged(self):
        result = self.run_cli("demo")

        self.assertEqual(result.returncode, 0, result.stderr)
        saved_tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        self.assertTrue(saved_tasks[0]["done"])
        self.assertFalse(saved_tasks[1]["done"])

    def test_unknown_id_does_not_change_existing_save(self):
        self.tasks_file.write_text(
            json.dumps([{"id": 7, "title": "Custom task", "done": False}]),
            encoding="utf-8",
        )
        original_contents = self.tasks_file.read_bytes()

        result = self.run_cli("done", "99")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("No task with ID 99.", result.stdout)
        self.assertEqual(self.tasks_file.read_bytes(), original_contents)

    def test_unknown_id_returns_nonzero_without_creating_save(self):
        result = self.run_cli("done", "99")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("No task with ID 99.", result.stdout)
        self.assertFalse(self.tasks_file.exists())

    def test_existing_task_data_and_extra_fields_survive_save(self):
        original_tasks = [
            {"id": 7, "title": "Custom task", "done": False, "notes": "keep this"}
        ]
        self.tasks_file.write_text(json.dumps(original_tasks), encoding="utf-8")

        result = self.run_cli("done", "7")

        self.assertEqual(result.returncode, 0, result.stderr)
        saved_tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_tasks[0]["title"], "Custom task")
        self.assertEqual(saved_tasks[0]["notes"], "keep this")
        self.assertTrue(saved_tasks[0]["done"])

    def test_malformed_json_is_reported_without_overwriting_file(self):
        malformed_contents = b'{"tasks": ['
        self.tasks_file.write_bytes(malformed_contents)

        result = self.run_cli("list")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not load tasks", result.stderr)
        self.assertEqual(self.tasks_file.read_bytes(), malformed_contents)


if __name__ == "__main__":
    unittest.main()
