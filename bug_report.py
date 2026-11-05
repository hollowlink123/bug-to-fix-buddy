"""Local bug report intake for Bug-to-Fix Buddy."""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


REPORTS_DIR = Path(__file__).with_name("bug_reports")


def create_report(description):
    """Build a new report after validating its description."""
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Report description cannot be empty.")

    return {
        "id": uuid.uuid4().hex,
        "description": description.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "received",
    }


def save_report(report, reports_dir=REPORTS_DIR):
    """Save one report to its own JSON file and return that file's path."""
    reports_dir = Path(reports_dir)
    report_path = reports_dir / f"{report['id']}.json"
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        with report_path.open("x", encoding="utf-8") as report_file:
            json.dump(report, report_file, indent=2, ensure_ascii=False)
            report_file.write("\n")
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise OSError(f"Could not save bug report to {report_path}: {error}") from error
    return report_path


def load_report(path):
    """Load a report JSON file."""
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as report_file:
            report = json.load(report_file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OSError(f"Could not load bug report from {path}: {error}") from error
    return report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1:
        print('Usage: python bug_report.py ["report description"]', file=sys.stderr)
        return 2

    description = argv[0] if argv else input("Describe the bug: ")
    try:
        report = create_report(description)
        report_path = save_report(report)
    except ValueError as error:
        print(f"Invalid report: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(error, file=sys.stderr)
        return 1

    print(f"Bug report {report['id']} received and saved to {report_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
