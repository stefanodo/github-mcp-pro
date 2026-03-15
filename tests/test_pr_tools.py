import importlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def import_main_with_env(env_overrides: dict[str, str | None]):
    original_env = os.environ.copy()
    try:
        for key, value in env_overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        if "main" in sys.modules:
            del sys.modules["main"]
        return importlib.import_module("main")
    finally:
        os.environ.clear()
        os.environ.update(original_env)


class PRToolTests(unittest.TestCase):
    def setUp(self):
        self.main = import_main_with_env(
            {
                "GITHUB_TOKEN": "unit_test_token",
                "REQUIRE_MCP_AUTH": "false",
                "MCP_AUTH_TOKEN": None,
            }
        )

    def test_build_findings_detects_eval(self):
        findings = self.main._build_findings("src/app.py", "+eval('x')")
        self.assertTrue(any(item.startswith("CRITICAL:") for item in findings))

    def test_build_findings_ignores_placeholder_in_readme(self):
        patch_text = "+token = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456'"
        findings = self.main._build_findings("README.md", patch_text)
        self.assertEqual(findings, [])

    def test_summarize_findings_counts(self):
        counts = self.main._summarize_findings(
            [
                "CRITICAL: a",
                "MAJOR: b",
                "MINOR: c",
                "INFO: d",
                "INFO: e",
            ]
        )
        self.assertEqual(counts["critical"], 1)
        self.assertEqual(counts["major"], 1)
        self.assertEqual(counts["minor"], 1)
        self.assertEqual(counts["info"], 2)

    def test_review_pr_requests_changes_on_critical(self):
        file_obj = SimpleNamespace(
            filename="src/app.py",
            patch="+eval('x')",
            changes=3,
        )
        pr = MagicMock()
        pr.get_files.return_value = [file_obj]
        pr.get_issue_comments.return_value = []
        pr.head = SimpleNamespace(sha="abc123")

        gh_repo = MagicMock()
        gh_repo.get_pull.return_value = pr
        gh_repo.get_commit.return_value = MagicMock()

        gh = MagicMock()
        gh.get_repo.return_value = gh_repo

        with patch.object(self.main, "Github", return_value=gh):
            result = self.main.review_pr("owner/repo", 12)

        self.assertIn("critical:1", result)
        pr.create_review.assert_called_once()
        self.assertEqual(pr.create_review.call_args.kwargs["event"], "REQUEST_CHANGES")

    def test_assess_pr_risk_posts_own_comment(self):
        files = [
            SimpleNamespace(filename="auth/login.py", additions=350),
            SimpleNamespace(filename="tests/test_login.py", additions=20),
        ]
        existing_comment = MagicMock()
        existing_comment.body = "<!-- mcp-risk-assessment --> old"

        pr = MagicMock()
        pr.get_files.return_value = files
        pr.get_issue_comments.return_value = [existing_comment]

        gh_repo = MagicMock()
        gh_repo.get_pull.return_value = pr

        gh = MagicMock()
        gh.get_repo.return_value = gh_repo

        with patch.object(self.main, "Github", return_value=gh):
            result = self.main.assess_pr_risk("owner/repo", 42)

        self.assertIn("Risk score:", result)
        existing_comment.edit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
