import asyncio
import importlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


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


class MainSecurityTests(unittest.TestCase):
    def test_import_fails_when_github_token_missing(self):
        command = [sys.executable, "-c", "import main"]
        result = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            env={**os.environ, "GITHUB_TOKEN": "", "REQUIRE_MCP_AUTH": "false"},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing required GITHUB_TOKEN", result.stderr + result.stdout)

    def test_import_fails_for_placeholder_token(self):
        command = [sys.executable, "-c", "import main"]
        result = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            env={**os.environ, "GITHUB_TOKEN": "your_token_here", "REQUIRE_MCP_AUTH": "false"},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder value", result.stderr + result.stdout)

    def test_sanitize_error_redacts_tokens(self):
        main = import_main_with_env(
            {
                "GITHUB_TOKEN": "ci_selfcheck_token_value_12345",
                "REQUIRE_MCP_AUTH": "false",
                "MCP_AUTH_TOKEN": None,
            }
        )

        message = "oops ghp_" + ("A" * 24) + " and github_pat_" + ("B" * 24)
        redacted = main._sanitize_error(message)

        self.assertNotIn("ghp_", redacted)
        self.assertNotIn("github_pat_", redacted)
        self.assertIn("[REDACTED_TOKEN]", redacted)

    def test_static_token_verifier_accepts_expected_token(self):
        main = import_main_with_env(
            {
                "GITHUB_TOKEN": "ci_selfcheck_token_value_12345",
                "REQUIRE_MCP_AUTH": "false",
                "MCP_AUTH_TOKEN": None,
            }
        )

        verifier = main.StaticTokenVerifier("expected-secret")
        valid = asyncio.run(verifier.verify_token("expected-secret"))
        invalid = asyncio.run(verifier.verify_token("wrong-secret"))

        self.assertIsNotNone(valid)
        self.assertIn("mcp:access", valid.scopes)
        self.assertIsNone(invalid)


if __name__ == "__main__":
    unittest.main()
