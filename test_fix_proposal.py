import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch as mock_patch

from bug_report import create_report, save_report
from fix_proposal import (
    _read_multiline_patch,
    create_proposal,
    format_preview,
    load_proposal_by_id,
    load_report_by_id,
    load_review,
    main as proposal_main,
    proposal_digest,
    record_decision,
    save_proposal,
)


class FixProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.reports_dir = self.root / "bug_reports"
        self.proposals_dir = self.root / "fix_proposals"
        self.reviews_dir = self.proposals_dir / "reviews"
        self.target_dir = self.root / "target project"
        self.target_dir.mkdir()
        self.report = create_report("The settings page crashes")
        save_report(self.report, self.reports_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_proposal(self, summary="Guard the missing setting"):
        return create_proposal(
            self.report,
            summary,
            "The setting is optional and can be absent.",
            "Check for the setting before reading it.",
            "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n",
            self.target_dir,
        )

    def test_load_saved_report_by_id_and_missing_report(self):
        loaded = load_report_by_id(self.report["id"], self.reports_dir)
        self.assertEqual(loaded, self.report)
        with self.assertRaises(OSError):
            load_report_by_id("missing-report", self.reports_dir)

    def test_proposals_are_unique_pending_and_saved_separately(self):
        first = self.make_proposal()
        second = self.make_proposal()
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["status"], "pending")
        first_path = save_proposal(first, self.proposals_dir)
        second_path = save_proposal(second, self.proposals_dir)
        self.assertNotEqual(first_path, second_path)
        self.assertEqual(load_proposal_by_id(first["id"], self.proposals_dir), first)

    def test_target_directory_is_canonical_and_covered_by_proposal_hash(self):
        proposal = self.make_proposal()
        path = save_proposal(proposal, self.proposals_dir)
        original_digest = proposal_digest(proposal["id"], self.proposals_dir)
        self.assertEqual(proposal["target_directory"], os.path.normcase(str(self.target_dir.resolve())))

        other_target = self.root / "another project"
        other_target.mkdir()
        contents = json.loads(path.read_text(encoding="utf-8"))
        contents["target_directory"] = str(other_target.resolve())
        path.write_text(json.dumps(contents), encoding="utf-8")

        self.assertNotEqual(proposal_digest(proposal["id"], self.proposals_dir), original_digest)

    def test_multiline_patch_reader_preserves_all_lines_until_terminator(self):
        patch = (
            "--- a/sample.py\n"
            "+++ b/sample.py\n"
            "@@ -1 +1 @@\n"
            "-value = 1\n"
            "+value = 2\n"
        )
        stream = io.StringIO(patch + "END_PATCH\nextra input\n")

        self.assertEqual(_read_multiline_patch(stream), patch)
        self.assertEqual(stream.readline(), "extra input\n")

    def test_multiline_patch_reader_rejects_missing_terminator(self):
        with self.assertRaisesRegex(ValueError, "END_PATCH"):
            _read_multiline_patch(io.StringIO("--- a/sample.py\n"))

    def test_preview_is_readable_and_includes_version_hash(self):
        proposal = self.make_proposal()
        save_proposal(proposal, self.proposals_dir)
        digest = proposal_digest(proposal["id"], self.proposals_dir)
        preview = format_preview(proposal, digest)
        for expected in (proposal["id"], "pending", proposal["summary"], proposal["rationale"], proposal["proposed_change"], digest, proposal["target_id"]):
            self.assertIn(expected, preview)
        self.assertNotIn(str(self.target_dir), preview)
        self.assertIn(f"Unified diff patch:\n{proposal['patch']}", preview)

    def test_approval_or_rejection_is_bound_to_exact_proposal_version(self):
        approved = self.make_proposal()
        rejected = self.make_proposal("Keep current behavior")
        save_proposal(approved, self.proposals_dir)
        save_proposal(rejected, self.proposals_dir)
        approved_digest = proposal_digest(approved["id"], self.proposals_dir)
        rejected_digest = proposal_digest(rejected["id"], self.proposals_dir)

        approval = record_decision(
            approved["id"], "approve", approved_digest, self.proposals_dir, self.reviews_dir
        )
        rejection = record_decision(
            rejected["id"], "reject", rejected_digest, self.proposals_dir, self.reviews_dir
        )
        self.assertEqual(approval["decision"], "approved")
        self.assertEqual(approval["proposal_sha256"], approved_digest)
        self.assertEqual(approval["target_directory"], approved["target_directory"])
        self.assertEqual(approval["target_id"], approved["target_id"])
        self.assertEqual(rejection["decision"], "rejected")
        self.assertEqual(load_review(approved["id"], self.reviews_dir), approval)
        self.assertEqual(load_review(rejected["id"], self.reviews_dir), rejection)

    def test_changed_version_cannot_use_old_preview_approval(self):
        proposal = self.make_proposal()
        path = save_proposal(proposal, self.proposals_dir)
        reviewed_digest = proposal_digest(proposal["id"], self.proposals_dir)
        contents = json.loads(path.read_text(encoding="utf-8"))
        contents["proposed_change"] = "Changed after review"
        path.write_text(json.dumps(contents), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "changed since preview"):
            record_decision(
                proposal["id"], "approve", reviewed_digest, self.proposals_dir, self.reviews_dir
            )
        self.assertIsNone(load_review(proposal["id"], self.reviews_dir))

    def test_missing_or_modified_target_metadata_fails_closed(self):
        proposal = self.make_proposal()
        path = save_proposal(proposal, self.proposals_dir)
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("target_directory")
        data.pop("target_id")
        path.write_text(json.dumps(data), encoding="utf-8")
        digest = proposal_digest(proposal["id"], self.proposals_dir)

        with self.assertRaisesRegex(ValueError, "missing target directory metadata"):
            record_decision(proposal["id"], "approve", digest, self.proposals_dir, self.reviews_dir)
        self.assertIsNone(load_review(proposal["id"], self.reviews_dir))

    def test_target_directory_must_exist_and_be_a_directory(self):
        with self.assertRaisesRegex(ValueError, "must exist"):
            self.make_proposal_target(self.root / "missing")
        file_path = self.root / "not-a-directory"
        file_path.write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must be a directory"):
            self.make_proposal_target(file_path)

    def test_cli_sanitizes_storage_os_errors(self):
        stderr = io.StringIO()
        with mock_patch(
            "fix_proposal.load_proposal_by_id",
            side_effect=OSError(r"C:\Users\private\proposal.json: denied"),
        ), redirect_stderr(stderr):
            result = proposal_main(["show", "proposal-id"])

        self.assertEqual(result, 1)
        self.assertEqual(stderr.getvalue(), "OSError: local storage operation failed.\n")
        self.assertNotIn("private", stderr.getvalue())

    def make_proposal_target(self, target):
        return create_proposal(
            self.report,
            "Guard the missing setting",
            "The setting is optional and can be absent.",
            "Check for the setting before reading it.",
            "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n",
            target,
        )

    def test_proposal_cannot_be_overwritten_and_revision_gets_new_id(self):
        proposal = self.make_proposal()
        path = save_proposal(proposal, self.proposals_dir)
        original_bytes = path.read_bytes()
        with self.assertRaises(OSError):
            save_proposal(proposal, self.proposals_dir)

        revision = self.make_proposal("Guard the missing setting and log it")
        revision_path = save_proposal(revision, self.proposals_dir)
        self.assertNotEqual(proposal["id"], revision["id"])
        self.assertEqual(path.read_bytes(), original_bytes)
        self.assertNotEqual(path, revision_path)

    def test_invalid_or_duplicate_decision_is_rejected_without_source_changes(self):
        proposal = self.make_proposal()
        save_proposal(proposal, self.proposals_dir)
        digest = proposal_digest(proposal["id"], self.proposals_dir)
        source = self.root / "sample.py"
        source.write_text("value = 1\n", encoding="utf-8")
        source_before = source.read_bytes()

        with self.assertRaisesRegex(ValueError, "must be 'approve' or 'reject'"):
            record_decision(proposal["id"], "maybe", digest, self.proposals_dir, self.reviews_dir)
        record_decision(proposal["id"], "approve", digest, self.proposals_dir, self.reviews_dir)
        with self.assertRaisesRegex(ValueError, "already recorded"):
            record_decision(proposal["id"], "reject", digest, self.proposals_dir, self.reviews_dir)
        self.assertEqual(source.read_bytes(), source_before)


if __name__ == "__main__":
    unittest.main()
