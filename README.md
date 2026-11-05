# Bug-to-Fix Buddy

Bug-to-Fix Buddy is a human-reviewed, AI-assisted bug investigation and repair workflow built for the WeMakeDevs Flip the Switch hackathon.

It demonstrates how an AI agent can investigate a reported software bug, identify its likely cause, prepare a reviewable code patch, and apply that patch after human approval.

The project combines a Python-based bug and patch management workflow with agent collaboration through Switch and Slack.

## The Problem

Debugging software involves more than identifying an error. Developers need to understand the cause, evaluate a proposed change, avoid unintended modifications, and verify that the fix works.

Bug-to-Fix Buddy explores a workflow in which an AI agent assists with investigation and patch preparation while a person retains control over approving and applying changes.

## How It Works

The workflow has six main stages:

1. **Report:** A user submits a description of the bug.
2. **Investigate:** The AI agent inspects the selected project and investigates the reported behavior.
3. **Propose:** The agent prepares a fix proposal containing its rationale, proposed change, and unified diff.
4. **Review:** A person reviews the proposal and approves or rejects it.
5. **Apply:** The approved patch is previewed and applied after confirmation.
6. **Verify:** Tests and other checks are used to verify the resulting behavior.

Human approval is required before applying a proposed source-code patch. Git operations such as committing and pushing are separate actions.

## Key Features

- Bug report creation and JSON-based storage.
- Fix proposals containing a summary, rationale, proposed change, and unified diff.
- SHA-256 hashes binding approval decisions to proposal contents.
- Separate approval and rejection records.
- Patch preview before application.
- Validation of supported unified diff operations.
- Protection against unsupported paths, symlinks, and mismatched patch context.
- Temporary-file replacement and rollback attempts for multi-file patch application.
- Automated tests for the Python application and workflow components.

## Project Architecture

The repository separates the workflow into several Python components.

| File | Responsibility |
|---|---|
| `bug_report.py` | Creates and loads bug reports |
| `fix_proposal.py` | Creates proposals, previews them, and records approval or rejection decisions |
| `fix_apply.py` | Validates, previews, and applies approved patches |
| `todo.py` | Small Python application used for demonstrating bugs and fixes |
| `test_bug_report.py` | Tests bug report behavior |
| `test_fix_proposal.py` | Tests proposal and decision handling |
| `test_fix_apply.py` | Tests patch application |
| `test_todo.py` | Tests the to-do application |

The to-do application is the demonstration target, not the limit of the intended agent workflow. Bug-to-Fix Buddy is designed to investigate different projects selected for individual tasks.

## Requirements

- Python 3
- Git
- A terminal
- Switch and Slack for the collaboration demonstration

The Python application and workflow tools use the Python standard library.

## Getting Started

Clone the repository:

```powershell
git clone https://github.com/hollowlink123/bug-to-fix-buddy.git
cd bug-to-fix-buddy
```

Check Python:

```powershell
py --version
```

On systems where the `py` launcher is unavailable, use `python` or `python3` instead.

### Run the To-Do Demonstration

Run the demonstration:

```powershell
py todo.py demo
```

List the tasks:

```powershell
py todo.py list
```

Complete a task by its ID:

```powershell
py todo.py done 2
```

If `tasks.json` does not exist, the application starts with two example tasks. Successful completion commands save the updated task data.

The JSON file is stored beside `todo.py`.

## The Demonstration Bugs

The to-do application has been used to demonstrate two different bug scenarios.

### 1. Task ID and List Position

The original bug involved treating a task ID as a Python list position.

Task IDs start at 1, whereas Python list positions start at 0. Using an ID directly as an index can therefore select the wrong task.

The correction searches for a task using its actual ID:

```python
matching_task = next(
    (task for task in tasks if task["id"] == task_id),
    None,
)
```

This ensures that the application selects the task whose ID matches the requested ID.

### 2. Duplicate Task IDs

A separate bug was identified in saved JSON data.

The application previously accepted multiple tasks with the same ID. Since completion searched for the first matching ID, it could silently update only one of the duplicate tasks.

The fix validates IDs while loading tasks and rejects duplicates before the application can modify the task data.

A regression test verifies that duplicate IDs produce an error and leave the original JSON file unchanged.

## Bug Report and Fix Proposal

### Create a bug report

```powershell
py bug_report.py "Describe the bug"
```

Bug report JSON files are stored under `bug_reports/` and ignored by Git.

### Create a fix proposal

For an existing report:

```powershell
py fix_proposal.py create <report-id>
```

The CLI requests:

- Proposal summary
- Rationale
- Proposed change
- Unified diff patch

### Preview a proposal

```powershell
py fix_proposal.py show <proposal-id>
```

The preview displays the proposal's SHA-256 hash. This hash covers the complete saved proposal JSON.

### Record an approval or rejection

After manually verifying the decision in the collaboration workflow:

```powershell
py fix_proposal.py decide <proposal-id> approve --sha256 <sha256>
```

To reject the proposal:

```powershell
py fix_proposal.py decide <proposal-id> reject --sha256 <sha256>
```

Decisions are stored separately under `fix_proposals/reviews/`.

The original proposal is not overwritten. A revision is recorded as a new proposal with a new ID.

The CLI records manually verified decisions; it does not independently authenticate a Switch or Slack user.

## Preview and Apply an Approved Fix

After a proposal has been approved, run:

```powershell
py fix_apply.py <proposal-id> <project-directory>
```

The tool displays the proposed changes and requires the user to type the proposal ID to continue.

The patch application tool:

- Accepts supported unified diffs that modify existing UTF-8 files.
- Rejects new or deleted files and renames.
- Rejects traversal paths, absolute paths, and symlinks.
- Checks that patch context matches the existing source.
- Does not execute commands supplied by a proposal.
- Attempts to restore files if a replacement fails.

Application results are stored under `fix_proposals/applications/` when the result record can be written.

## Switch and Slack Collaboration

The agent's investigation and proposed-fix workflow was demonstrated in a Switch room connected to the Slack channel `#bug-to-fix-demo`.

During the demonstration:

1. A bug was discussed with the agent.
2. The agent inspected the relevant project code.
3. It explained the identified problem and proposed a code change.
4. The project owner reviewed and approved the proposal.
5. The approved change was applied and verified.

Switch and Slack were used for collaboration and communication.

The Python CLI, proposal management, approval records, and patch application are implemented in this repository. An automatic integration connecting the Python application directly to Switch and Slack is not implemented.

## Tests

Run the complete test suite:

```powershell
py -m unittest -v
```

The tests cover:

- Bug report creation and loading.
- Proposal creation and preview.
- Approval and rejection records.
- Proposal hash verification.
- Patch validation and application.
- To-do task listing and completion.
- Task completion persistence.
- Unknown task IDs.
- Invalid and malformed task data.
- Duplicate task ID rejection.
- Preservation of the original task file when duplicate IDs are detected.

## Limitations and Security Considerations

- The to-do application is a demonstration target, not a complete task-management application.
- It starts with two example tasks and does not provide commands to add, edit, or delete tasks.
- Task data is stored locally in `tasks.json`.
- Malformed JSON and invalid task data must be repaired manually.
- Proposal decisions are local records of manually verified messages. The CLI cannot authenticate the identity of the person who sent a message.
- The patch tool supports a restricted subset of unified diff operations.
- Proposal-supplied commands are not executed.
- Rollback is attempted if file replacement fails, but restoration is not guaranteed if rollback also fails.
- If writing an application result fails after source files have been replaced, source files may remain changed without a saved application record.
- Written agent instructions guide behavior but do not replace host-level permission and sandbox enforcement.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Project Goal

Bug-to-Fix Buddy demonstrates how AI-assisted software debugging can be organized into a reviewable workflow.

The agent helps investigate problems and prepare changes, but people retain control over approving and applying code modifications.
