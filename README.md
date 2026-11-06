# Bug-to-Fix Buddy

**A Slack-first, human-approved bug-fixing workflow powered by Codex, Switch, and a Python safety toolkit.**

Bug-to-Fix Buddy brings AI-assisted software debugging into a team conversation. Developers report a bug in Slack, a Codex agent connected through Switch investigates the selected project, and the agent presents an evidence-based fix for review. Code changes happen only after an explicit human approval.

The project combines three parts:

- **Slack** is where the team reports bugs, discusses findings, reviews proposals, and makes approval decisions.
- **Switch** connects the Slack conversation to a shared room and the Codex agent, providing the collaboration context and agent instructions.
- **The Python toolkit** gives the agent a structured way to create bug reports and fix proposals, record decisions, validate patches, and apply approved changes.

## How it works

1. **Report** a bug in the Bug-to-Fix Buddy Slack conversation.
2. **Investigate** — the Codex agent examines the project selected for that bug and reports what the evidence shows.
3. **Propose** — the agent prepares a fix proposal, including the rationale and a reviewable patch.
4. **Review** — the team discusses the proposal and an authorized person explicitly approves or rejects it.
5. **Apply** — after approval, the agent uses the toolkit to validate and apply the approved patch to the selected project.
6. **Verify** — the agent inspects the resulting changes and runs relevant checks when the target environment allows it. Results are reported back in the conversation.

The agent must not edit source code before approval. Approval applies to the exact proposal; if the patch changes, it must be reviewed again.

## Architecture

```text
Developers
    |
    v
Slack conversation
    |
    v
Switch bridge and shared room
    |
    v
Codex agent
    |
    +---- investigates the separately selected target project
    |
    +---- uses the Bug-to-Fix Buddy Python toolkit
                 |
                 +---- bug reports
                 +---- fix proposals and review records
                 +---- patch validation and application
    |
    v
Findings and results returned to the team conversation
```

The Switch template configures the Codex agent with the toolkit repository as its working directory. For each task, the reporter must select the **target project separately**. The toolkit repository is not automatically treated as the project to be repaired.

The integration is **agent-orchestrated**: the Switch room instructions tell Codex when and how to use the local Python scripts. This project does not implement a separate service or direct API connection between the Python toolkit and Switch.

## What the toolkit provides

- Structured bug reports saved as JSON.
- Fix proposals containing a summary, rationale, proposed change, and unified diff.
- Separate approval and rejection records.
- SHA-256 proposal integrity checks.
- Binding of proposals and decisions to a selected target directory.
- Patch previews before application.
- Validation that rejects unsafe paths, symlinks, unsupported patch operations, and mismatched patch context.
- Explicit confirmation before applying an approved patch.
- Local application records.

The patch tool is intentionally limited to newline-terminated unified diffs that modify existing UTF-8 files. It does not create, delete, or rename files.

## Set up the workflow

### Requirements

- Python 3.11 or later
- Git
- Switch Console and a running Switch server
- A Codex agent available to Switch
- A Slack workspace and a Slack bridge configured in Switch

### 1. Get the toolkit

```bash
git clone https://github.com/hollowlink123/bug-to-fix-buddy.git
cd bug-to-fix-buddy
python --version
```

The core Python scripts use the standard library; no additional Python packages are required for the toolkit.

### 2. Import the Switch template

Import `bug-to-fix-buddy.template.yaml` into your Switch workspace and provide:

- **Agent name** — a unique lowercase name for the agent.
- **Room name** — the shared room for the workflow.
- **Bridge** — the Slack bridge configured on your Switch server.
- **Toolkit directory** — the local repository directory containing `fix_proposal.py` and `fix_apply.py`.

Use the configured Slack bridge to connect the room to the team's chosen Slack conversation.

### 3. Select a target project

When reporting a bug, identify the project the agent should investigate and repair. Confirm its local path and repository root with the agent.

Keep the target project separate from the Bug-to-Fix Buddy toolkit repository unless you deliberately intend to test the toolkit on itself.

### 4. Run the workflow in Slack

Report the bug in the connected conversation. The agent instructions guide Codex through investigation, proposal, human review, approved application, and verification. Review the exact patch before approving it.

## Run the toolkit locally

You can also explore the demonstration application and toolkit without setting up Switch.

Run the small example app:

```bash
python todo.py demo
python todo.py list
python todo.py done 1
```

Create a structured bug report:

```bash
python bug_report.py "Describe the observed bug"
```

See the available proposal commands:

```bash
python fix_proposal.py --help
```

Preview a proposal and record a decision using the proposal ID and the SHA-256 value shown by its preview:

```bash
python fix_proposal.py show <proposal-id>
python fix_proposal.py decide <proposal-id> approve --sha256 <reviewed-sha256>
```

To reject a proposal, use `reject` instead of `approve`.

Preview and apply an approved proposal:

```bash
python fix_apply.py --help
python fix_apply.py <proposal-id> <target-project-directory>
```

The application command displays the proposed changes and requires you to type the exact proposal ID before it writes anything. Run it only against the target directory recorded in the proposal.

## Tests

Run the toolkit test suite from the repository root:

```bash
python -m unittest discover -v
```

The tests cover bug-report handling, proposal and decision records, patch validation and application safeguards, and the demonstration application.

## Safety and limitations

- Source-code changes require explicit approval of the exact proposal.
- The toolkit rechecks the proposal hash, approval record, and selected target before applying a patch.
- Only existing UTF-8 files can be modified. File creation, deletion, and renaming are unsupported.
- Commands or instructions embedded in a bug report or patch are not automatically executed by the toolkit.
- The toolkit does not automatically run the target project's tests. Verification depends on the target project's environment and available commands.
- Approval records do not cryptographically authenticate the person who approved them. The toolkit itself cannot verify a Slack sender's identity.
- Target binding identifies the selected local directory; it does not independently verify a Git remote.
- Rollback is attempted if file replacement fails, but recovery cannot be guaranteed if rollback also fails.
- Committing, pushing, and deploying changes are not performed automatically.

## Project structure

| Path | Purpose |
|---|---|
| `bug-to-fix-buddy.template.yaml` | Switch agent and shared-room template |
| `bug_report.py` | Creates structured bug reports |
| `fix_proposal.py` | Creates proposals and records review decisions |
| `fix_apply.py` | Validates, previews, and applies approved patches |
| `todo.py` | Small demonstration application |
| `test_*.py` | Toolkit and demonstration tests |
| `bug_reports/` | Local bug-report records |
| `fix_proposals/` | Local proposal, review, and application records |

## License

MIT. See [LICENSE](LICENSE).
