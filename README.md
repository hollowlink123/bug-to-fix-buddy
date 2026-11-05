# Bug-to-Fix Buddy

A beginner-friendly demo for the WeMakeDevs Flip the Switch hackathon. The project pairs a small Python to-do list with a bug-investigation workflow demonstrated through Switch.

## The problem

When a task is marked complete by its ID, a program can accidentally update a different task. Finding and explaining a bug also takes time, especially when a report does not include the details a developer needs.

Bug-to-Fix Buddy demonstrates how a teammate can report an issue, an AI agent can inspect the code and explain a proposed fix, and a person can review the change.

## What is implemented

The Python command-line app in `todo.py`:

- Starts with two example tasks.

- Lists tasks and marks a task complete by its ID.

- Provides a `demo` command that completes task 1.

- Saves tasks as JSON in `tasks.json` next to `todo.py`, so completed tasks persist across command runs.

- Uses only the Python standard library; no external Python packages are required.

The task-ID bug was that IDs started at 1 but were mistakenly used as Python list positions, which start at 0. That caused task 1 to update the second task, and the last task ID could raise an error. The fix updates the task found by its ID:

```python
matching_task["done"] = True
```

## Run the demo

Open a terminal in this project folder. To show the demo, which marks task 1 complete and saves it, run:

```powershell
py todo.py demo
```

To list tasks:

```powershell
py todo.py list
```

To complete task 2 directly:

```powershell
py todo.py done 2
```

If `tasks.json` does not exist, the program starts with the two example tasks. A successful `done` or `demo` command saves the updated tasks there. If the JSON is malformed or contains invalid task data, the program reports an error and leaves the file untouched; repair the file manually before running the app again.

## Tests

Run the automated tests from the project folder with:

```powershell
py -m unittest -v
```

The six tests cover:

1. A fresh run lists the example tasks without creating a save file.

2. Completing task 2 persists across separate command runs.

3. `demo` saves task 1 as done and leaves task 2 unfinished.

4. An unknown task ID does not change saved data.

5. Existing task fields, including extra fields, survive a save.

6. Malformed JSON is reported without being overwritten.

The project owner reported all six tests passing on Windows and manually verified that task 1 remains done after running `demo` and then `list` in separate commands.

## Bug investigation workflow demonstrated through Switch

The report, code investigation, explanation, proposed fix, and owner review were demonstrated in the Switch room connected to `#bug-to-fix-demo`. The agent inspected the project and explained the task-ID bug; the owner reviewed and approved the fix. This workflow is a human-reviewed collaboration process shown through Switch conversations.

The Python CLI and JSON persistence are implemented in this repository. Automated bug tracking and an automatic integration between the Python app and Switch are not implemented.

## Current limitations

- There are no commands to add, edit, or delete tasks; the app starts with two examples unless the JSON file is edited manually.

- Task data is stored locally in `tasks.json` beside the script, so the project folder must be writable and the file should be backed up if its contents matter.

- Malformed JSON or invalid task data must be repaired manually; the app preserves the file and does not attempt recovery.

- Automated bug tracking or app-to-Switch integration is not implemented.
