"""Local storage and review records for Bug-to-Fix Buddy proposals.

This module never applies proposals or writes to project source files.
"""

import argparse
import hashlib
import hmac
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from bug_report import REPORTS_DIR, load_report


PROPOSALS_DIR = Path(__file__).with_name("fix_proposals")
REVIEWS_DIR = PROPOSALS_DIR / "reviews"


def _read_json(path, description):
    try:
        with Path(path).open("r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OSError(f"Could not load {description} from {path}: {error}") from error


def load_report_by_id(report_id, reports_dir=REPORTS_DIR):
    """Load a previously saved bug report by its exact ID."""
    if not report_id or Path(str(report_id)).name != str(report_id):
        raise ValueError("Report ID must be a non-empty ID, not a path.")
    path = Path(reports_dir) / f"{report_id}.json"
    report = load_report(path)
    if not isinstance(report, dict) or report.get("id") != report_id:
        raise ValueError(f"Saved report ID does not match {report_id}.")
    return report


def create_proposal(report, summary, rationale, proposed_change):
    """Build a pending proposal. A revision is a new proposal with a new ID."""
    if not isinstance(report, dict) or not report.get("id"):
        raise ValueError("A saved bug report is required to create a proposal.")
    fields = {
        "summary": summary,
        "rationale": rationale,
        "proposed_change": proposed_change,
    }
    for name, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Proposal {name.replace('_', ' ')} cannot be empty.")

    return {
        "id": uuid.uuid4().hex,
        "report_id": report["id"],
        "summary": summary.strip(),
        "rationale": rationale.strip(),
        "proposed_change": proposed_change.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }


def save_proposal(proposal, proposals_dir=PROPOSALS_DIR):
    """Create a proposal file once; an existing ID can never be overwritten."""
    proposals_dir = Path(proposals_dir)
    proposal_path = proposals_dir / f"{proposal['id']}.json"
    try:
        proposals_dir.mkdir(parents=True, exist_ok=True)
        with proposal_path.open("x", encoding="utf-8") as proposal_file:
            json.dump(proposal, proposal_file, indent=2, ensure_ascii=False)
            proposal_file.write("\n")
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise OSError(f"Could not save proposal to {proposal_path}: {error}") from error
    return proposal_path


def load_proposal_by_id(proposal_id, proposals_dir=PROPOSALS_DIR):
    """Load one immutable proposal by its ID."""
    if not proposal_id or Path(str(proposal_id)).name != str(proposal_id):
        raise ValueError("Proposal ID must be a non-empty ID, not a path.")
    path = Path(proposals_dir) / f"{proposal_id}.json"
    proposal = _read_json(path, "proposal")
    if not isinstance(proposal, dict) or proposal.get("id") != proposal_id:
        raise ValueError(f"Saved proposal ID does not match {proposal_id}.")
    return proposal


def proposal_digest(proposal_id, proposals_dir=PROPOSALS_DIR):
    """Return SHA-256 of the exact saved bytes a reviewer previews."""
    path = Path(proposals_dir) / f"{proposal_id}.json"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise OSError(f"Could not read proposal version from {path}: {error}") from error


def load_review(proposal_id, reviews_dir=REVIEWS_DIR):
    """Load the separate review decision for a proposal, if one exists."""
    review_path = Path(reviews_dir) / f"{proposal_id}.json"
    if not review_path.exists():
        return None
    review = _read_json(review_path, "proposal review")
    if not isinstance(review, dict) or review.get("proposal_id") != proposal_id:
        raise ValueError(f"Saved review does not match proposal {proposal_id}.")
    return review


def format_preview(proposal, digest=None, review=None):
    """Format proposal details and the hash used to bind an explicit decision."""
    status = review["decision"] if review else proposal["status"]
    lines = [
        f"Proposal: {proposal['id']}",
        f"Bug report: {proposal['report_id']}",
        f"Status: {status}",
        f"Summary: {proposal['summary']}",
        f"Rationale: {proposal['rationale']}",
        f"Proposed change: {proposal['proposed_change']}",
        f"Created: {proposal['created_at']}",
    ]
    if digest:
        lines.append(f"Version SHA-256: {digest}")
    if review:
        lines.append(f"Decision recorded: {review['decided_at']}")
    return "\n".join(lines)


def record_decision(
    proposal_id,
    decision,
    expected_sha256,
    proposals_dir=PROPOSALS_DIR,
    reviews_dir=REVIEWS_DIR,
):
    """Record one explicit decision only if it matches the reviewed bytes."""
    if decision not in ("approve", "reject"):
        raise ValueError("Decision must be 'approve' or 'reject'.")
    if not expected_sha256:
        raise ValueError("The reviewed proposal SHA-256 is required.")

    proposal = load_proposal_by_id(proposal_id, proposals_dir)
    current_digest = proposal_digest(proposal_id, proposals_dir)
    if not hmac.compare_digest(current_digest, expected_sha256.lower()):
        raise ValueError("Proposal changed since preview; review the current version again.")

    reviews_dir = Path(reviews_dir)
    review_path = reviews_dir / f"{proposal_id}.json"
    review = {
        "proposal_id": proposal_id,
        "proposal_sha256": current_digest,
        "decision": "approved" if decision == "approve" else "rejected",
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        reviews_dir.mkdir(parents=True, exist_ok=True)
        with review_path.open("x", encoding="utf-8") as review_file:
            json.dump(review, review_file, indent=2, ensure_ascii=False)
            review_file.write("\n")
    except FileExistsError as error:
        raise ValueError(f"A decision is already recorded for proposal {proposal_id}.") from error
    except OSError as error:
        raise OSError(f"Could not record decision at {review_path}: {error}") from error
    return review


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create and review local fix proposals.")
    commands = parser.add_subparsers(dest="command", required=True)

    create_parser = commands.add_parser("create", help="create a proposal for a bug report")
    create_parser.add_argument("report_id")
    show_parser = commands.add_parser("show", help="preview a proposal")
    show_parser.add_argument("proposal_id")
    decide_parser = commands.add_parser("decide", help="approve or reject a reviewed version")
    decide_parser.add_argument("proposal_id")
    decide_parser.add_argument("decision", choices=("approve", "reject"))
    decide_parser.add_argument("--sha256", required=True, help="hash shown by the preview command")
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            report = load_report_by_id(args.report_id)
            proposal = create_proposal(
                report,
                input("Proposal summary: "),
                input("Rationale: "),
                input("Proposed change: "),
            )
            path = save_proposal(proposal)
            print(f"Created pending proposal {proposal['id']} at {path}.")
            return 0
        if args.command == "show":
            proposal = load_proposal_by_id(args.proposal_id)
            digest = proposal_digest(args.proposal_id)
            review = load_review(args.proposal_id)
            print(format_preview(proposal, digest, review))
            return 0

        review = record_decision(args.proposal_id, args.decision, args.sha256)
        print(f"Recorded {review['decision']} for proposal {args.proposal_id}.")
        print("This records a manually verified Switch decision; the CLI cannot authenticate its sender.")
        return 0
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
