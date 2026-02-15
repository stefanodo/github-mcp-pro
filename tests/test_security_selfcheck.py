import importlib
import io
import os
import unittest
from contextlib import redirect_stdout


class SecuritySelfcheckTests(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_main_check_completes(self):
        os.environ["GITHUB_TOKEN"] = "ci_selfcheck_token_value_12345"
        os.environ["REQUIRE_MCP_AUTH"] = "false"

        module = importlib.import_module("scripts.security_selfcheck")

        out = io.StringIO()
        with redirect_stdout(out):
            module.main_check()

        self.assertIn("security_selfcheck_ok", out.getvalue())


if __name__ == "__main__":
    unittest.main()
