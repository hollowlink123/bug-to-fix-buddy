import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch as mock_patch

from bug_report import create_report
from fix_apply import apply_approved_proposal, main as apply_main, parse_patch, preview_application
from fix_proposal import (
    canonical_target_directory,
    create_proposal,
    proposal_digest,
    record_decision,
    save_proposal,
)


class FixApplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.other_project = self.root / "other project"
        self.other_project.mkdir()
        self.proposals = self.root / "proposals"
        self.reviews = self.proposals / "reviews"
        self.applications = self.proposals / "applications"
        self.source = self.project / "sample.py"
        self.source.write_text("value = 1\n", encoding="utf-8")
        (self.other_project / "sample.py").write_text("value = 1\n", encoding="utf-8")
        self.patch_text = "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n"

    def tearDown(self):
        self.temp.cleanup()

    def make_proposal(self, decision="approve", patch_text=None):
        proposal = create_proposal(
            create_report("Sample issue"), "Change value", "It is incorrect.",
            "Change the value to two.", patch_text or self.patch_text, self.project,
        )
        save_proposal(proposal, self.proposals)
        if decision:
            digest = proposal_digest(proposal["id"], self.proposals)
            record_decision(proposal["id"], decision, digest, self.proposals, self.reviews)
        return proposal

    def test_preview_and_apply_requires_approved_exact_proposal_and_confirmation(self):
        proposal = self.make_proposal()
        preview, _, digest = preview_application(proposal["id"], self.project, self.proposals, self.reviews)
        self.assertIn("value = 1", preview)
        self.assertIn("value = 2", preview)
        self.assertIn(digest, preview)
        self.assertIn(proposal["target_id"], preview)
        self.assertNotIn(str(self.project), preview)
        with self.assertRaisesRegex(ValueError, "exact proposal ID"):
            apply_approved_proposal(proposal["id"], self.project, "no", self.proposals, self.reviews, self.applications)
        result = apply_approved_proposal(proposal["id"], self.project, proposal["id"], self.proposals, self.reviews, self.applications)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(self.source.read_text(encoding="utf-8"), "value = 2\n")
        application = json.loads((self.applications / f"{proposal['id']}.json").read_text())
        self.assertEqual(application["status"], "applied")
        self.assertEqual(application["target_id"], proposal["target_id"])
        self.assertEqual(application["files"], ["sample.py"])
        self.assertNotIn(str(self.root), json.dumps(application))
        self.assertNotIn(str(self.root), preview)

    def test_different_directory_is_rejected_even_when_patch_matches(self):
        proposal = self.make_proposal()
        with self.assertRaisesRegex(ValueError, "does not match the approved proposal target"):
            preview_application(proposal["id"], self.other_project, self.proposals, self.reviews)
        with self.assertRaisesRegex(ValueError, "does not match the approved proposal target"):
            apply_approved_proposal(
                proposal["id"], self.other_project, proposal["id"],
                self.proposals, self.reviews, self.applications,
            )
        self.assertEqual((self.other_project / "sample.py").read_text(encoding="utf-8"), "value = 1\n")

    def test_legacy_proposal_without_target_metadata_is_rejected(self):
        proposal = self.make_proposal(decision=None)
        path = self.proposals / f"{proposal['id']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("target_directory")
        data.pop("target_id")
        path.write_text(json.dumps(data), encoding="utf-8")
        review_path = self.reviews / f"{proposal['id']}.json"
        self.reviews.mkdir(parents=True, exist_ok=True)
        review_path.write_text(json.dumps({
            "proposal_id": proposal["id"],
            "proposal_sha256": proposal_digest(proposal["id"], self.proposals),
            "decision": "approved",
            "decided_at": "legacy",
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing target directory metadata"):
            preview_application(proposal["id"], self.project, self.proposals, self.reviews)

    def test_tampered_review_target_is_rejected(self):
        proposal = self.make_proposal()
        review_path = self.reviews / f"{proposal['id']}.json"
        original = json.loads(review_path.read_text(encoding="utf-8"))
        for field, value in (
            ("target_directory", str(self.other_project.resolve())),
            ("target_id", "different-target-binding"),
        ):
            review = dict(original)
            review[field] = value
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Approval target does not match"):
                preview_application(proposal["id"], self.project, self.proposals, self.reviews)

    def test_pending_and_rejected_proposals_are_never_applied(self):
        for decision in (None, "reject"):
            proposal = self.make_proposal(decision)
            with self.assertRaisesRegex(ValueError, "Only an approved"):
                preview_application(proposal["id"], self.project, self.proposals, self.reviews)

    def test_changed_proposal_bytes_after_approval_are_rejected(self):
        proposal = self.make_proposal()
        path = self.proposals / f"{proposal['id']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["patch"] = data["patch"].replace("value = 2", "value = 3")
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after approval"):
            preview_application(proposal["id"], self.project, self.proposals, self.reviews)

    def test_changed_proposal_target_after_approval_is_rejected(self):
        proposal = self.make_proposal()
        path = self.proposals / f"{proposal['id']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["target_directory"] = canonical_target_directory(self.other_project)
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Approval target does not match"):
            preview_application(proposal["id"], self.other_project, self.proposals, self.reviews)

    def test_cli_sanitizes_filesystem_os_errors(self):
        stderr = io.StringIO()
        with mock_patch(
            "fix_apply.preview_application",
            side_effect=OSError(f"{self.project}: denied"),
        ), redirect_stderr(stderr):
            result = apply_main(["proposal-id", str(self.project)])

        self.assertEqual(result, 1)
        self.assertEqual(stderr.getvalue(), "OSError: local filesystem operation failed.\n")
        self.assertNotIn(str(self.project), stderr.getvalue())

    def test_mismatched_source_and_unsupported_or_unsafe_patches_are_rejected(self):
        self.source.write_text("value = 99\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match"):
            parse_patch(self.patch_text, self.project)
        for path in ("../outside.py", "/outside.py", "sub\\file.py"):
            text = self.patch_text.replace("sample.py", path)
            with self.assertRaises(ValueError):
                parse_patch(text, self.project)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            parse_patch("diff --git a/sample.py b/sample.py\n" + self.patch_text, self.project)

    def test_symlink_target_is_rejected(self):
        link = self.project / "linked.py"
        try:
            link.symlink_to(self.source)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable in this environment")
        link_patch = self.patch_text.replace("sample.py", "linked.py")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            parse_patch(link_patch, self.project)

    def test_multi_file_failure_restores_files_and_records_failure(self):
        second = self.project / "second.py"
        second.write_text("count = 1\n", encoding="utf-8")
        patch_text = self.patch_text + "--- a/second.py\n+++ b/second.py\n@@ -1 +1 @@\n-count = 1\n+count = 2\n"
        parsed = parse_patch(patch_text, self.project)
        self.assertEqual([path.name for path, _, _ in parsed], ["sample.py", "second.py"])
        proposal = self.make_proposal(patch_text=patch_text)
        real_replace = __import__("os").replace

        def fail_second(source, target):
            if Path(target) == second and Path(source).name != "second.py":
                raise OSError("simulated replacement failure")
            return real_replace(source, target)

        with mock_patch("fix_apply.os.replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "simulated"):
                apply_approved_proposal(proposal["id"], self.project, proposal["id"], self.proposals, self.reviews, self.applications)
        self.assertEqual(self.source.read_text(encoding="utf-8"), "value = 1\n")
        self.assertEqual(second.read_text(encoding="utf-8"), "count = 1\n")
        record = json.loads((self.applications / f"{proposal['id']}.json").read_text())
        self.assertEqual(record["status"], "failed")
        self.assertNotIn(str(self.root), record["error"])
        self.assertEqual(record["files"], ["sample.py", "second.py"])


if __name__ == "__main__":
    unittest.main()
