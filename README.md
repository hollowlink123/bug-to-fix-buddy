# Bug-to-Fix Buddy

**Bug-to-Fix Buddy** is a human-reviewed, AI-assisted workflow for investigating software bugs and applying proposed code fixes.

An AI agent helps investigate a reported issue, understand the relevant code, and prepare a proposed patch. A person reviews the proposal and explicitly approves it before the Python toolkit can apply the change.

The project explores how AI-assisted debugging can be made more structured, reviewable, and controlled.

## How It Works

The workflow follows six stages:

1. **Report:** A user describes a software bug.
2. **Investigate:** The AI agent examines the selected project and investigates the reported behavior.
3. **Propose:** The agent prepares a fix proposal with an explanation and unified diff patch.
4. **Review:** A person examines the proposed changes and approves or rejects the proposal.
5. **Apply:** The Python toolkit validates the approval, previews the patch, and applies it after explicit confirmation.
6. **Verify:** The resulting changes are inspected and relevant tests are run separately.

Human approval is required before a proposed patch is applied. Committing and pushing changes are separate operations and are not performed automatically.

## Features

- **Bug reports:** Create and store structured bug reports as JSON files.
- **Fix proposals:** Prepare proposals containing a summary, rationale, proposed change, and unified diff.
- **Approval records:** Store approval or rejection decisions separately from the original proposal.
- **Proposal integrity:** Use SHA-256 hashes to detect changes to a proposal after it has been reviewed.
- **Target binding:** Bind proposals and approval records to the selected project directory and target binding ID.
- **Patch preview:** Display proposed file changes before application.
- **Patch validation:** Reject unsupported patch operations, unsafe paths, symlinks, and mismatched patch context.
- **Safer application:** Check the approved proposal and target again before writing changes.
- **Application records:** Record the result of a patch application.
- **Automated tests:** Test bug reporting, proposal handling, patch validation, application, and the demonstration application.

## Project Structure

| File or directory | Purpose |
|---|---|
| `bug_report.py` | Creates and loads bug reports |
| `fix_proposal.py` | Creates proposals, previews them, and records approval or rejection |
| `fix_apply.py` | Validates and applies approved patches |
| `todo.py` | Small demonstration application used for bug scenarios |
| `bug_reports/` | Stores generated bug reports |
| `fix_proposals/` | Stores proposals, review decisions, and application records |
| `test_bug_report.py` | Tests bug report handling |
| `test_fix_proposal.py` | Tests proposal and review handling |
| `test_fix_apply.py` | Tests patch validation and application |
| `test_todo.py` | Tests the demonstration application |
| `bug-to-fix-buddy.template.yaml` | Switch agent and room template |

Generated reports, proposals, and application data are local workflow records rather than source files.

## Requirements

- Python 3.11 or later
- Git
- A terminal
- Switch Console, if you want to use the agent collaboration workflow

The Python toolkit uses the Python standard library. No external Python package installation is required for the core scripts.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/hollowlink123/bug-to-fix-buddy.git
cd bug-to-fix-buddy
```

Check your Python installation:

```bash
python --version
```

Run the demonstration:

```bash
python todo.py demo
```

List the demonstration tasks:

```bash
python todo.py list
```

Mark a task as complete:

```bash
python todo.py done 1
```

The demonstration application starts with two example tasks when no saved task file exists. Task data is stored locally in `tasks.json`.

## Using the Python Toolkit

### 1. Create a bug report

```bash
python bug_report.py "Describe the bug"
```

The report is saved as a JSON file in `bug_reports/`.

### 2. Create and review a fix proposal

Use the proposal CLI to create a proposal for a saved bug report:

```bash
python fix_proposal.py --help
```

The proposal workflow collects the proposed fix, its rationale, and a unified diff patch. Use the CLI help for the exact arguments supported by the current version.

Preview a saved proposal:

```bash
python fix_proposal.py show <proposal-id>
```

The preview displays the proposal details and its SHA-256 hash.

### 3. Record a decision

After reviewing the exact proposal, record an approval using the hash shown in its preview:

```bash
python fix_proposal.py decide <proposal-id> approve --sha256 <reviewed-sha256>
```

To reject it:

```bash
python fix_proposal.py decide <proposal-id> reject --sha256 <reviewed-sha256>
```

A proposal cannot be approved using a hash that does not match its saved contents. The original proposal is preserved, and a revised proposal receives a new ID.

### 4. Preview and apply an approved patch

Check the application command:

```bash
python fix_apply.py --help
```

The application workflow requires the proposal ID and selected project directory. It validates the proposal, approval record, and target before showing the preview. The user must type the exact proposal ID to confirm application.

## Target and Patch Safety

The toolkit is deliberately restricted.

- Each proposal records the canonical target directory and a target binding ID.
- The approval record is bound to the same target and proposal hash.
- The selected target and approval are checked before preview and again before writing.
- Missing or invalid target metadata causes the operation to stop.
- Only newline-terminated unified diffs that modify existing UTF-8 files are supported.
- File creation, deletion, and renaming are not supported.
- Absolute paths, directory traversal, symlinks, and mismatched patch context are rejected.
- Commands supplied inside a proposal are not executed.
- The toolkit does not automatically run the target project's tests.

The target binding identifies the selected local directory. It does not independently verify a Git remote or authenticate the person approving a proposal.

## Switch Collaboration

The project includes a Switch template for configuring the Bug-to-Fix Buddy agent and its shared room instructions.

The intended collaboration workflow is:

1. A user reports a bug in the shared room.
2. The agent investigates the selected project.
3. The agent explains its findings and prepares a proposed change.
4. A person reviews the proposal and explicitly approves or rejects it.
5. The Python toolkit validates and applies an approved patch.
6. The resulting changes are inspected and tested.

**Important:** Switch provides the agent collaboration and instructions. The Python scripts provide the local bug-report, proposal, approval-record, and patch-application functionality. A direct automatic integration connecting the Python toolkit to Switch is not implemented.

Agent instructions do not replace operating-system permissions or sandbox restrictions.

## Running Tests

Run the test suite from the repository root:

```bash
python -m unittest discover -v
```

The tests cover:

- Bug report creation and loading
- Proposal creation and preview
- Approval and rejection records
- Proposal hash verification
- Target and approval binding
- Patch parsing and validation
- Patch application safeguards
- Task listing and completion
- Invalid task data and duplicate task IDs

Only report tests as passing after actually running them.

## Limitations

- The to-do application is a demonstration target, not a complete task-management product.
- The patch tool supports a restricted subset of unified diffs.
- The toolkit does not guarantee compatibility with every repository.
- Approval records do not cryptographically authenticate the approver's identity.
- The toolkit does not automatically run project tests.
- Rollback is attempted if file replacement fails, but restoration cannot be guaranteed if rollback also fails.
- A failure to save an application record after source files have changed can leave modified files without a corresponding saved record.
- Committing, pushing, and deploying changes are outside the automatic workflow.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Project Goal

Bug-to-Fix Buddy explores a safer, more reviewable way to use AI during software debugging.

The agent assists with investigation and patch preparation, while people retain control over reviewing, approving, and applying code changes.