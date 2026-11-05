# Bug-to-Fix Buddy

Bug-to-Fix Buddy is a human-reviewed bug-fixing workflow built around a small Python to-do list. It demonstrates how a bug report can be investigated by an AI agent, turned into a proposed code fix, reviewed by a person, and applied after approval.

Built for the WeMakeDevs Flip the Switch hackathon.

## The Problem

A program can accidentally update the wrong task when it treats a task ID as a list position. Finding the cause of a bug and preparing a safe fix can also take time.

Bug-to-Fix Buddy demonstrates a workflow where an AI agent helps investigate a reported issue and explain a proposed fix, while a person remains responsible for reviewing and approving the change.

## How It Works

1. **Report a bug:** A person submits a description of the problem.
2. **Investigate:** An AI agent inspects the code and explains the cause.
3. **Propose a fix:** A proposal contains the rationale, proposed change, and unified diff patch.
4. **Review:** A person reviews the proposal and records an approval or rejection.
5. **Apply:** The approved patch is previewed and applied after confirmation.
6. **Verify:** Tests and a manual check confirm the behavior.

## The Demonstration Bug

The to-do list uses task IDs starting at 1, while Python list positions start at 0. Using a task ID directly as a list position can select the wrong task.

The fix searches for the task by its ID:

```python
matching_task = next(
    (task for task in tasks if task["id"] == task_id),
    None,
)
```

This ensures that completing task 1 updates task 1, rather than task 2.

## Features

The Python command-line app in `todo.py`:

- Starts with two example tasks.
- Lists tasks and marks a task complete by its ID.
- Provides a `demo` command that completes task 1.
- Saves tasks as JSON in `tasks.json` beside `todo.py`.
- Preserves completed tasks across separate command runs.
- Uses only the Python standard library.

The project also includes:

- Local bug report intake in `bug_report.py`.
- Fix proposal creation, preview, and decision recording in `fix_proposal.py`.
- A patch preview and application tool in `fix_apply.py`.
- Automated tests for the to-do app and its persistence behavior.

## Run the To-Do Demo

Open a terminal in the project folder.

Run the demo:

```powershell
py todo.py demo
```

List the tasks:

```powershell
py todo.py list
```

Complete task 2 directly:

```powershell
py todo.py done 2
```

If `tasks.json` does not exist, the program starts with the two example tasks. Successful `done` and `demo` commands save the updated tasks.

If the JSON file is malformed or contains invalid task data, the program reports an error and leaves the file untouched. The file must be repaired manually before running the app again.

## Bug Report and Fix Proposal

Submit a bug report:

```powershell
py bug_report.py "Describe the bug"
```

Report JSON files are stored under `bug_reports/` and ignored by Git.

Create a proposal for an existing report:

```powershell
py fix_proposal.py create <report-id>
```

The CLI asks for the proposal summary, rationale, proposed change, and unified diff patch.

Preview a proposal:

```powershell
py fix_proposal.py show <proposal-id>
```

The preview displays the proposal's SHA-256 hash. The hash covers the complete proposal JSON, binding the approval to the proposal content.

Record a manually verified Switch decision:

```powershell
py fix_proposal.py decide --sha2 <sha256> <proposal-id> approve
```

Use `reject` instead of `approve` to reject the proposal.

Decisions are saved separately under `fix_proposals/reviews/`. Proposal JSON files are not overwritten. A revision is recorded as a new proposal with a new ID.

## Preview and Apply a Fix

After approval, preview and apply a proposal:

```powershell
py fix_apply.py <proposal-id> <project-directory>
```

The tool displays the complete changes and requires typing the proposal ID to continue.

It accepts supported unified diffs that update existing UTF-8 files. It rejects new or deleted files, renames, symlinks, traversal paths, unsupported syntax, and source content that differs from the patch context. It does not run commands supplied by a proposal.

The tool attempts to restore files if a replacement fails, but rollback is not guaranteed if restoration also fails. If saving the application result fails after source files have been replaced, the source files may be changed without a saved result.

Application results are stored under `fix_proposals/applications/` when the record can be written.

## Tests

Run the automated tests from the project folder:

```powershell
py -m unittest -v
```

The test suite checks:

- Listing example tasks on a fresh run.
- Completing tasks by ID.
- Saving task completion across command runs.
- Ensuring the demo completes task 1 without changing task 2.
- Handling unknown task IDs.
- Preserving task fields during saving.
- Reporting malformed JSON without overwriting it.

The workflow was manually verified by applying the approved patch in a separate demo copy and confirming that completing task 1 leaves task 2 unfinished.

## Switch Collaboration

The bug investigation and proposed fix were demonstrated in a Switch room connected to `#bug-to-fix-demo`.

The agent inspected the code and explained the task-ID bug. The project owner reviewed and approved the proposed fix before it was applied.

The Python CLI, proposal handling, patch application, and JSON persistence are implemented in this repository. The Switch investigation was demonstrated through conversations. Automated bug tracking and an automatic integration between the Python app and Switch are not implemented.

## Limitations

- The app starts with two example tasks. It does not include commands to add, edit, or delete tasks.
- Task data is stored locally in `tasks.json` beside the script.
- Malformed JSON or invalid task data must be repaired manually.
- Proposal decisions are local records of manually verified Switch messages. The CLI cannot independently authenticate the sender.
- The patch tool does not run proposal-supplied commands.
- Proposal, review, and application-result JSON files are ignored by Git.

## Project Goal

Bug-to-Fix Buddy demonstrates a human-reviewed AI-assisted bug-fixing workflow. An AI agent helps investigate a problem and prepare a code change, while a person retains control over approval and application.

