# Bug-to-Fix Buddy

A human-reviewed bug-fixing workflow connecting Slack, Switch, Codex, and a local Python toolkit.

Bug-to-Fix Buddy helps developers investigate software bugs, review proposed fixes, and apply changes only after explicit human approval.

## How it works

1. **Report:** A developer reports a bug in the connected Slack conversation.
2. **Investigate:** The local Codex agent investigates the separately selected target project.
3. **Propose:** The agent uses the Python toolkit to prepare a fix proposal containing its reasoning and a reviewable patch.
4. **Review:** A human reviews the proposal in Slack and explicitly approves or rejects it.
5. **Record:** The Codex agent records the manually verified decision using the toolkit.
6. **Apply:** The toolkit validates and applies the approved patch to the target project.
7. **Verify:** The agent inspects the changes and runs relevant checks when the target environment allows it.

The agent must not modify source code before approval. Approval applies to the exact proposal. If the patch changes, it must be reviewed again.

## Architecture

```text
              Developer
                  |
                  v
          Slack conversation
                  |
                  v
           Switch room/bridge
                  |
                  v
           Local Codex agent
                  |
          +-------+--------+
          |                |
          v                v
   Target project     Python toolkit
   Investigation     Bug reports
   and evidence      Fix proposals
          |          Review records
          |          Patch validation
          |                |
          +-------+--------+
                  |
                  v
             Fix proposal
                  |
                  v
          Human review in Slack
                  |
             Approval decision
                  |
                  v
           Codex records decision
                  |
                  v
           Python toolkit validates
             approved proposal
                  |
                  v
           Applies approved patch
                  |
                  v
             Target project
                  |
                  v
           Verification and report
```

The Switch template configures a local Codex agent with this repository as its working directory. The target project is selected separately for each task.

Switch connects the Slack conversation to the agent, Codex coordinates the workflow, and the Python toolkit handles bug reports, proposals, review records, validation and patch application. This is an agent-orchestrated integration, not a separate hosted service.

## Project structure

| Path | Purpose |
|---|---|
| `bug-to-fix-buddy.template.yaml` | Switch agent and room configuration |
| `bug_report.py` | Creates structured bug reports |
| `fix_proposal.py` | Creates proposals and records review decisions |
| `fix_apply.py` | Validates, previews and applies approved patches |
| `todo.py` | Demonstration application |
| `test_*.py` | Test suite |
| `bug_reports/` | Generated bug-report records |
| `fix_proposals/` | Proposal, review and application records |

## Components

- **Slack:** Bug reports, discussions, proposal reviews and approval decisions.
- **Switch:** Connects the Slack conversation to the local Codex agent.
- **Codex:** Investigates the selected project and coordinates the workflow.
- **Python toolkit:** Stores reports, creates proposals, records decisions, validates patches and applies approved changes.

## Features

- Structured bug reports stored as JSON.
- Fix proposals containing summaries, rationale, proposed changes and unified diffs.
- Separate approval and rejection records.
- SHA-256 proposal integrity checks.
- Target-directory binding.
- Patch previews before application.
- Validation against unsafe paths, symlinks and mismatched patch context.
- Explicit confirmation before applying approved patches.
- Local application records.

The patch tool supports updates to existing UTF-8 files. File creation, deletion and renaming are unsupported.

## Requirements

- Python 3.11 or later
- Git
- Switch Console and a running Switch server
- A Codex agent available to Switch
- A Slack workspace with a configured Slack bridge

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/hollowlink123/bug-to-fix-buddy.git
cd bug-to-fix-buddy
python --version
```

The Python toolkit uses the standard library and requires no additional Python packages.

### 2. Import the Switch template

Import `bug-to-fix-buddy.template.yaml` into your Switch workspace.

Configure these parameters:

- `agent_name`: Unique lowercase agent name.
- `room_name`: Name of the shared room.
- `bridge`: Slack bridge configured in Switch.
- `toolkit_directory`: Local path to this repository.

Connect the room to the desired Slack conversation through the configured bridge.

### 3. Select a target project

For each bug, identify the target project's local directory and confirm its repository root with the agent.

The target project and toolkit repository are separate. The toolkit must not automatically be treated as the project being repaired.

### 4. Start the workflow

Report a bug in the connected Slack conversation. The agent instructions guide it through investigation, proposal creation, human review, approved patch application and verification.

## Toolkit commands

These commands let you run the toolkit's individual operations from the terminal. In the integrated workflow, the Switch agent uses these same scripts to create proposals, record review decisions and apply approved patches.

### Demonstration application

Run the included demonstration application:

```bash
python todo.py demo
python todo.py list
python todo.py done 1
```

### Create a bug report

```bash
python bug_report.py "Describe the observed bug"
```

The command creates a JSON report and prints its report ID.

### Create a fix proposal

```bash
python fix_proposal.py create <report-id>
```

The command interactively asks for the target directory, proposal summary, rationale, proposed change and unified diff. Finish the patch input by entering `END_PATCH` on a line by itself.

### Preview a proposal

```bash
python fix_proposal.py show <proposal-id>
```

Review the proposed changes and note the SHA-256 value displayed in the preview.

### Record a review decision

```bash
python fix_proposal.py decide <proposal-id> approve --sha256 <reviewed-sha256>
```

Use `reject` instead of `approve` to reject the proposal.

The CLI records a manually verified decision; it cannot independently authenticate the person submitting it.

### Apply an approved proposal

```bash
python fix_apply.py --help
python fix_apply.py <proposal-id> <target-project-directory>
```

The application command validates the proposal and approval, displays the proposed changes and requires you to type the exact proposal ID before modifying files.

## Tests

Run the test suite from the repository root:

```bash
python -m unittest discover -v
```

Tests cover bug reports, proposals, review decisions, patch validation, application safeguards and the demonstration application.

## Safety and limitations

- Source-code changes require approval of the exact proposal.
- Proposal hashes, approval records and target-directory binding are checked before application.
- Only existing UTF-8 files can be modified. Creating, deleting and renaming files are unsupported.
- The toolkit does not automatically execute commands embedded in bug reports or patches.
- Target-project tests are not run automatically. Verification depends on the project's environment.
- Approval records do not cryptographically authenticate the approver or independently verify a Slack sender's identity.
- Target binding identifies a local directory but does not independently verify its Git remote.
- Rollback is attempted if file replacement fails, but recovery cannot be guaranteed if rollback also fails.
- Committing, pushing and deploying changes are not automatic.

## License

MIT. See [LICENSE](LICENSE).
