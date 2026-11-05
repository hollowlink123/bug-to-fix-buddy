"""Safely preview and apply a small, approved unified diff."""

import argparse
import difflib
import hmac
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from fix_proposal import (
    PROPOSALS_DIR,
    REVIEWS_DIR,
    load_proposal_by_id,
    load_review,
    proposal_digest,
)


APPLICATIONS_DIR = PROPOSALS_DIR / "applications"
_HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@$")


def _approved_proposal(proposal_id, proposals_dir, reviews_dir):
    proposal = load_proposal_by_id(proposal_id, proposals_dir)
    review = load_review(proposal_id, reviews_dir)
    if not review or review.get("decision") != "approved":
        raise ValueError("Only an approved proposal can be applied.")
    digest = proposal_digest(proposal_id, proposals_dir)
    if not hmac.compare_digest(digest, str(review.get("proposal_sha256", ""))):
        raise ValueError("Proposal content changed after approval.")
    if not isinstance(proposal.get("patch"), str) or not proposal["patch"].strip():
        raise ValueError("Proposal has no unified diff patch.")
    return proposal, digest


def _safe_target(root, name):
    if not name or "\\" in name or name.startswith("/") or ":" in name:
        raise ValueError(f"Unsafe patch path: {name!r}")
    if any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError(f"Unsafe patch path: {name!r}")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError(f"Unsafe patch path: {name!r}")
    root = Path(root).resolve(strict=True)
    target = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Patch paths cannot use symlinks: {name}")
    resolved = target.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError(f"Patch path must be an existing file inside the project: {name}")
    return resolved


def parse_patch(patch, project_dir):
    """Parse only ordinary unified diffs that update existing UTF-8 files."""
    if not isinstance(patch, str) or not patch.endswith("\n"):
        raise ValueError("Patch must be a newline-terminated unified diff.")
    lines = patch.splitlines()
    changes = []
    index = 0
    while index < len(lines):
        if index + 2 >= len(lines) or not lines[index].startswith("--- ") or not lines[index + 1].startswith("+++ "):
            raise ValueError("Unsupported patch format: expected --- and +++ file headers.")
        old_name = lines[index][4:]
        new_name = lines[index + 1][4:]
        if old_name.startswith("a/"):
            old_name = old_name[2:]
        if new_name.startswith("b/"):
            new_name = new_name[2:]
        if old_name != new_name or old_name == "/dev/null":
            raise ValueError("Patch must update an existing file without renaming it.")
        target = _safe_target(project_dir, old_name)
        try:
            with target.open("r", encoding="utf-8", newline="") as source_file:
                original = source_file.read()
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError(f"Could not read patch target {old_name} as UTF-8: {error}") from error
        original_lines = original.splitlines(keepends=True)
        line_ending = "\r\n" if "\r\n" in original else "\n"
        result = []
        source_position = 0
        index += 2
        saw_hunk = False
        while index < len(lines) and lines[index].startswith("@@ "):
            match = _HUNK.fullmatch(lines[index])
            if not match:
                raise ValueError("Unsupported or malformed unified diff hunk header.")
            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) is not None else 1
            new_count = int(match.group(4)) if match.group(4) is not None else 1
            hunk_start = max(old_start - 1, 0)
            if hunk_start < source_position or hunk_start > len(original_lines):
                raise ValueError(f"Patch hunk is out of order or outside {old_name}.")
            result.extend(original_lines[source_position:hunk_start])
            source_position = hunk_start
            consumed = produced = 0
            index += 1
            saw_hunk = True
            while (
                index < len(lines)
                and lines[index][:1] in (" ", "+", "-")
                and not (
                    lines[index].startswith("--- ")
                    and index + 1 < len(lines)
                    and lines[index + 1].startswith("+++ ")
                )
            ):
                line = lines[index]
                content = line[1:] + line_ending
                if line.startswith(" "):
                    if source_position >= len(original_lines) or original_lines[source_position] != content:
                        raise ValueError(f"Patch context does not match current contents of {old_name}.")
                    result.append(original_lines[source_position])
                    source_position += 1
                    consumed += 1
                    produced += 1
                elif line.startswith("-"):
                    if source_position >= len(original_lines) or original_lines[source_position] != content:
                        raise ValueError(f"Patch removal does not match current contents of {old_name}.")
                    source_position += 1
                    consumed += 1
                else:
                    result.append(content)
                    produced += 1
                index += 1
            if consumed != old_count or produced != new_count:
                raise ValueError("Unified diff hunk line counts do not match its header.")
        if not saw_hunk:
            raise ValueError("Each file section must contain at least one hunk.")
        if index < len(lines) and lines[index].startswith("\\"):
            raise ValueError("No-newline markers are not supported.")
        result.extend(original_lines[source_position:])
        changes.append((target, original.encode("utf-8"), "".join(result).encode("utf-8")))
    if not changes:
        raise ValueError("Patch contains no file changes.")
    if len({target for target, _, _ in changes}) != len(changes):
        raise ValueError("Patch contains duplicate file sections.")
    return changes


def preview_application(proposal_id, project_dir, proposals_dir=PROPOSALS_DIR, reviews_dir=REVIEWS_DIR):
    proposal, digest = _approved_proposal(proposal_id, proposals_dir, reviews_dir)
    changes = parse_patch(proposal["patch"], project_dir)
    lines = [f"Proposal {proposal_id} (approved; SHA-256 {digest})", "Files:"]
    for path, before, after in changes:
        lines.append(f"- {path}")
        old = before.decode("utf-8").splitlines(keepends=True)
        new = after.decode("utf-8").splitlines(keepends=True)
        lines.extend(difflib.unified_diff(old, new, fromfile=str(path), tofile=str(path)))
    return "\n".join(lines), changes, digest


def _write_temp(directory, data):
    handle = tempfile.NamedTemporaryFile(dir=directory, delete=False)
    try:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        return Path(handle.name)
    finally:
        handle.close()


def apply_approved_proposal(
    proposal_id, project_dir, confirmation, proposals_dir=PROPOSALS_DIR,
    reviews_dir=REVIEWS_DIR, applications_dir=APPLICATIONS_DIR,
):
    """Apply after ID confirmation, restoring all originals if a write fails."""
    preview, changes, digest = preview_application(proposal_id, project_dir, proposals_dir, reviews_dir)
    if confirmation != proposal_id:
        raise ValueError("Application requires typing the exact proposal ID shown in the preview.")
    # Recheck the exact approved bytes immediately before any file is written.
    _approved_proposal(proposal_id, proposals_dir, reviews_dir)
    replacements = {}
    backups = {}
    changed = []
    result = {
        "proposal_id": proposal_id, "proposal_sha256": digest,
        "status": "failed", "applied_at": datetime.now(timezone.utc).isoformat(),
        "files": [str(path) for path, _, _ in changes],
    }
    try:
        for path, original, updated in changes:
            if path.read_bytes() != original:
                raise ValueError(f"File changed after preview; review the patch again: {path}")
            replacements[path] = _write_temp(path.parent, updated)
            backups[path] = _write_temp(path.parent, original)
        for path, _, _ in changes:
            os.replace(replacements[path], path)
            changed.append(path)
        result["status"] = "applied"
    except Exception as error:
        rollback_errors = []
        for path in reversed(changed):
            try:
                os.replace(backups[path], path)
            except OSError as rollback_error:
                rollback_errors.append(f"{path}: {rollback_error}")
        result["error"] = str(error)
        if rollback_errors:
            result["rollback_errors"] = rollback_errors
        raise
    finally:
        for temporary in (*replacements.values(), *backups.values()):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        applications_dir = Path(applications_dir)
        applications_dir.mkdir(parents=True, exist_ok=True)
        result_path = applications_dir / f"{proposal_id}.json"
        with result_path.open("x", encoding="utf-8") as result_file:
            json.dump(result, result_file, indent=2)
            result_file.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview and apply an approved code fix.")
    parser.add_argument("proposal_id")
    parser.add_argument("project_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        preview, _, _ = preview_application(args.proposal_id, args.project_dir)
        print(preview)
        confirmation = input("Type the proposal ID to apply these exact changes: ")
        result = apply_approved_proposal(args.proposal_id, args.project_dir, confirmation)
        print(f"Application {result['status']}; result saved under {APPLICATIONS_DIR}.")
        return 0
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
