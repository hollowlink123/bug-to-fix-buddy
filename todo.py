import json
import os
import sys
import tempfile
from pathlib import Path


TASKS_FILE = Path(__file__).with_name("tasks.json")
DEFAULT_TASKS = [
    {"id": 1, "title": "Write the project README", "done": False},
    {"id": 2, "title": "Review the demo bug report", "done": False},
]


class InvalidTaskDataError(ValueError):
    """Raised when the saved task file does not contain valid task data."""


def load_tasks(path=TASKS_FILE):
    """Load saved tasks, or return fresh examples when no save exists."""
    path = Path(path)
    if not path.exists():
        return [task.copy() for task in DEFAULT_TASKS]

    with path.open("r", encoding="utf-8") as task_file:
        loaded_tasks = json.load(task_file)

    if not isinstance(loaded_tasks, list):
        raise InvalidTaskDataError("the top-level JSON value must be a list")

    seen_ids = set()
    for index, task in enumerate(loaded_tasks):
        if not isinstance(task, dict):
            raise InvalidTaskDataError(f"task {index + 1} must be an object")
        if isinstance(task.get("id"), bool) or not isinstance(task.get("id"), int):
            raise InvalidTaskDataError(f"task {index + 1} must have an integer ID")
        if task["id"] in seen_ids:
            raise InvalidTaskDataError(f"duplicate task ID {task['id']}")
        seen_ids.add(task["id"])
        if not isinstance(task.get("title"), str):
            raise InvalidTaskDataError(f"task {index + 1} must have a string title")
        if not isinstance(task.get("done"), bool):
            raise InvalidTaskDataError(f"task {index + 1} must have a boolean done value")

    return loaded_tasks


def save_tasks(tasks, path=TASKS_FILE):
    """Atomically save tasks, keeping a partial write from replacing the save."""
    path = Path(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as task_file:
            temporary_path = Path(task_file.name)
            json.dump(tasks, task_file, indent=2, ensure_ascii=False)
            task_file.write("\n")

        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def show_tasks(tasks):
    if not tasks:
        print("No tasks yet.")
        return

    for task in tasks:
        status = "done" if task["done"] else "not done"
        print(f'{task["id"]}. {task["title"]} — {status}')


def complete_task(task_id, tasks):
    matching_task = next(
        (task for task in tasks if task["id"] == task_id),
        None,
    )

    if matching_task is None:
        print(f"No task with ID {task_id}.")
        return False

    matching_task["done"] = True
    print(f"Marked task {task_id} as done.")
    return True


def run_demo(tasks):
    print("Tasks before completing task 1:")
    show_tasks(tasks)

    print("\nTrying to complete task 1...")
    completed = complete_task(1, tasks)

    print("\nTasks after completing task 1:")
    show_tasks(tasks)
    return completed


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv or (argv[0] == "list" and len(argv) == 1):
        command = "list"
    elif argv[0] == "done" and len(argv) == 2:
        try:
            task_id = int(argv[1])
        except ValueError:
            print("Task ID must be a number.")
            return 2
        command = "done"
    elif argv[0] == "demo" and len(argv) == 1:
        command = "demo"
    else:
        print("Usage:")
        print("  python todo.py list")
        print("  python todo.py done <task-id>")
        print("  python todo.py demo")
        return 2

    try:
        tasks = load_tasks()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, InvalidTaskDataError) as error:
        print(f"Could not load tasks from {TASKS_FILE}: {error}", file=sys.stderr)
        return 1

    if command == "list":
        show_tasks(tasks)
        return 0

    if command == "done":
        changed = complete_task(task_id, tasks)
        if not changed:
            return 1
    else:
        changed = run_demo(tasks)

    if changed:
        try:
            save_tasks(tasks)
        except OSError as error:
            print(f"Could not save tasks to {TASKS_FILE}: {error}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
