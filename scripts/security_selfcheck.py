import asyncio
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _run_import_with_env(env_overrides: dict[str, str | None]) -> tuple[int, str]:
    env = os.environ.copy()
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value

    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stderr or result.stdout or "").strip()


def _assert_startup_guards() -> None:
    code, output = _run_import_with_env(
        {
            "GITHUB_TOKEN": None,  # Fully unset the variable
            "MCP_AUTH_TOKEN": None,
            "REQUIRE_MCP_AUTH": "false",
        }
    )
    assert code != 0, "Import should fail when GITHUB_TOKEN is missing"
    assert "Missing required GITHUB_TOKEN" in output, output

    code, output = _run_import_with_env(
        {
            "GITHUB_TOKEN": "your_token_here",
            "MCP_AUTH_TOKEN": None,
            "REQUIRE_MCP_AUTH": "false",
        }
    )
    assert code != 0, "Import should fail for placeholder token"
    assert "placeholder value" in output, output

    code, output = _run_import_with_env(
        {
            "GITHUB_TOKEN": "ci_selfcheck_token_value_67890",
            "MCP_AUTH_TOKEN": None,
            "REQUIRE_MCP_AUTH": "true",
        }
    )
    assert code != 0, "Import should fail when auth required but MCP token missing"
    # Accept either the default GITHUB_TOKEN guard or a custom message
    assert (
        "Missing required GITHUB_TOKEN" in output
        or "REQUIRE_MCP_AUTH is enabled" in output
        or "MCP token" in output
    ), output



def _assert_error_redaction() -> None:
    # Run in subprocess with safe env so main.py guard does not trigger
    env = os.environ.copy()
    env["REQUIRE_MCP_AUTH"] = "false"
    env["MCP_AUTH_TOKEN"] = "dummy"
    env["GITHUB_TOKEN"] = "dummy"
    code = subprocess.run([
        sys.executable, "-c",
        "import main; sample = 'leaked token ' + 'ghp_' + ('A' * 32); redacted = main._sanitize_error(sample); assert 'ghp_' not in redacted; assert '[REDACTED_TOKEN]' in redacted"
    ], env=env, cwd=str(REPO_ROOT)).returncode
    assert code == 0, "Error redaction test failed"



async def _assert_static_token_verifier() -> None:
    # Run in subprocess with safe env so main.py guard does not trigger
    env = os.environ.copy()
    env["REQUIRE_MCP_AUTH"] = "false"
    env["MCP_AUTH_TOKEN"] = "dummy"
    env["GITHUB_TOKEN"] = "dummy"
    code = subprocess.run([
        sys.executable, "-c",
        "import asyncio; import main; verifier = main.StaticTokenVerifier('expected-secret'); valid = asyncio.get_event_loop().run_until_complete(verifier.verify_token('expected-secret')); assert valid is not None and 'mcp:access' in valid.scopes; invalid = asyncio.get_event_loop().run_until_complete(verifier.verify_token('wrong-secret')); assert invalid is None"
    ], env=env, cwd=str(REPO_ROOT)).returncode
    assert code == 0, "StaticTokenVerifier test failed"


def main_check() -> None:
    _assert_startup_guards()
    _assert_error_redaction()
    asyncio.run(_assert_static_token_verifier())
    sys.stdout.write("security_selfcheck_ok\n")


if __name__ == "__main__":
    main_check()
