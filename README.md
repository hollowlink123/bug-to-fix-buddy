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

Local bug report intake is implemented in `bug_report.py`. Submit a report with `py bug_report.py "Describe the bug"`; report JSON files are stored under `bug_reports/` and ignored by Git.

Fix proposals are implemented in `fix_proposal.py`. Create a proposal for an existing report with `py fix_proposal.py create <report-id>` and enter its summary, rationale, human-readable proposed change, and unified diff patch when prompted. Preview it with `py fix_proposal.py show <proposal-id>`. The preview displays the exact proposal file's SHA-256. Because the hash covers the complete proposal JSON, it binds approval to the explanation and patch. Record a manually verified Switch decision with `py fix_proposal.py decide <proposal-id> approve --sha256 <sha256>` or use `reject` instead. Decisions are saved separately under `fix_proposals/reviews/`; proposal JSON files and their contents are never overwritten. Any revision is a new proposal with a new ID. Git ignores proposal, review, and application-result JSON files.

The local Python CLI records a manually verified decision received through Switch. It cannot independently authenticate the Switch sender. After approval, preview and apply a proposal with `py fix_apply.py <proposal-id> <project-directory>`. The tool displays the complete changes and requires typing the proposal ID to continue. It accepts only simple unified diffs that update existing UTF-8 files; it rejects new/deleted files, renames, symlinks, traversal paths, unsupported syntax, and source content that differs from the patch context. It does not run proposal-supplied commands. If file replacement fails, the tool attempts to restore files it already replaced, but restoration is not guaranteed if rollback also fails. If writing the application-result record fails after files were replaced successfully, the source files may be changed without a saved result. Application results are stored under `fix_proposals/applications/` when the record can be written.

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

The Python CLI and JSON persistence are implemented in this repository. Automated bug tracking and an automatic integration between the Python app and Switch are not implemented; a person must verify the Switch decision before recording it locally.

## Current limitations

- There are no commands to add, edit, or delete tasks; the app starts with two examples unless the JSON file is edited manually.

- Task data is stored locally in `tasks.json` beside the script, so the project folder must be writable and the file should be backed up if its contents matter.

- Malformed JSON or invalid task data must be repaired manually; the app preserves the file and does not attempt recovery.

- Automated bug tracking or app-to-Switch integration is not implemented.

- Proposal decisions are local records of manually verified Switch messages. The CLI does not authenticate senders or apply proposed code changes.
