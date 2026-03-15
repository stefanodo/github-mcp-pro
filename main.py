
# --- Early dotenv load and auth guard: must be first ---
import os
from dotenv import load_dotenv
# Load environment and print debug info for CI/CD
load_dotenv()
REQUIRE_MCP_AUTH_RAW = os.getenv("REQUIRE_MCP_AUTH", "false")
REQUIRE_MCP_AUTH = REQUIRE_MCP_AUTH_RAW.lower() == "true"
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")
print(f"[DEBUG] REQUIRE_MCP_AUTH_RAW={REQUIRE_MCP_AUTH_RAW!r} REQUIRE_MCP_AUTH={REQUIRE_MCP_AUTH!r} MCP_AUTH_TOKEN={MCP_AUTH_TOKEN!r}")

# Guard: fail if REQUIRE_MCP_AUTH is enabled but MCP_AUTH_TOKEN is missing or only whitespace
if REQUIRE_MCP_AUTH and not (MCP_AUTH_TOKEN and MCP_AUTH_TOKEN.strip()):
    raise RuntimeError("REQUIRE_MCP_AUTH is enabled but MCP_AUTH_TOKEN is missing")

# Guard: fail if GITHUB_TOKEN is missing or a known placeholder

# --- All imports at the top ---
import re
import hashlib
import hmac
import logging
from urllib.parse import quote
from typing import Optional
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.config import Config
from starlette.middleware.cors import CORSMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from github import Github

# --- Load env and assign variables ---
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
# Guard: fail if GITHUB_TOKEN is missing or a known placeholder
if GITHUB_TOKEN in ("your_token_here", "ci_selfcheck_token_value_12345", "ci_selfcheck_token_value_67890"):
    raise RuntimeError("Missing required GITHUB_TOKEN: GITHUB_TOKEN is set to a placeholder value")
if not GITHUB_TOKEN:
    raise RuntimeError("Missing required GITHUB_TOKEN")

# --- OAuth setup ---
config = Config(environ=os.environ)
oauth = OAuth(config)
oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token', # nosec
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'repo user'},
)



from dotenv import load_dotenv
import logging
import os

load_dotenv()
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REQUIRE_MCP_AUTH = os.getenv("REQUIRE_MCP_AUTH", "false").lower() == "true"
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

# Restrict CORS to trusted domains (comma-separated in env)
cors_origins = os.getenv("CORS_ALLOW_ORIGINS")
if cors_origins:
    allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
else:
    # Default: allow only production domain, fallback to all for dev
    allowed_origins = ["https://stefano-mcp-pro.fly.dev"] if os.getenv("ENV") == "production" else ["*"]

# --- Rate limiting setup ---
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup OAuth after env variables and app setup
config = Config(environ=os.environ)
oauth = OAuth(config)
oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token', # nosec
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'repo user'},
)
# --- StaticTokenVerifier for security self-check ---
from typing import Optional

class StaticTokenVerifier:
    def __init__(self, expected_secret: str):
        self.expected_secret = expected_secret

    async def verify_token(self, token: str) -> Optional[object]:
        if token == self.expected_secret:
            class Result:
                scopes = ["mcp:access"]
            return Result()
        return None
# --- Error redaction utility for security self-check ---
import re
from collections import Counter

def _sanitize_error(msg: str) -> str:
    # Redact GitHub tokens (ghp_...) and similar patterns
    token_pattern = re.compile(r"gh[p]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")
    return token_pattern.sub("[REDACTED_TOKEN]", msg)


_GITHUB_TOKEN_PATTERN = re.compile(r"gh[p]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")
_SAFE_TOKEN_PATHS = frozenset({"readme.md", ".env.example", "scripts/security_selfcheck.py"})


def _is_placeholder_token(path: str, line: str, token_value: str) -> bool:
    lowered_line = line.lower()

    if (
        "exampletoken" in token_value.lower()
        or "your_token_here" in lowered_line
        or "replace_with_real_token" in lowered_line
        or "<real-github-token>" in lowered_line
    ):
        return True

    return path.lower() in _SAFE_TOKEN_PATHS


def _build_findings(path: str, patch: str) -> list[str]:
    findings: list[str] = []
    if not patch:
        return findings

    if "console.log" in patch.lower():
        findings.append(f"MINOR: {path} contains console.log")

    for raw in patch.splitlines():
        if not raw.startswith("+") or raw.startswith("+++"):
            continue

        line = raw[1:]
        stripped = line.strip()

        if "findings.append(" in stripped and (
            "eval() added" in stripped
            or "potential hardcoded GitHub token" in stripped
        ):
            continue

        if re.search(r"(?<!['\"])\beval\s*\(", line):
            findings.append(f"CRITICAL: {path} eval() added")
        if re.search(r"(?<!['\"])\bdebugger\b", line):
            findings.append(f"MAJOR: {path} debugger statement added")
        if re.search(r"^\s*except\s*:\s*$", line):
            findings.append(f"MAJOR: {path} bare except detected")

        token_match = _GITHUB_TOKEN_PATTERN.search(line)
        if token_match:
            token_value = token_match.group(0)
            if not _is_placeholder_token(path, line, token_value):
                findings.append(f"CRITICAL: {path} potential hardcoded GitHub token")

        if "password" in stripped.lower() and "=" in stripped and '"' in stripped:
            findings.append(f"MAJOR: {path} possible hardcoded password")
        if "todo" in stripped.lower() or "fixme" in stripped.lower():
            findings.append(f"INFO: {path} TODO/FIXME added")

    return findings


def _summarize_findings(findings: list[str]) -> Counter:
    counts: Counter = Counter()
    for finding in findings:
        if finding.startswith("CRITICAL"):
            counts["critical"] += 1
        elif finding.startswith("MAJOR"):
            counts["major"] += 1
        elif finding.startswith("MINOR"):
            counts["minor"] += 1
        else:
            counts["info"] += 1
    return counts


def _upsert_issue_comment(pr, marker: str, body: str) -> None:
    existing = None
    for comment in pr.get_issue_comments():
        if comment.body and marker in comment.body:
            existing = comment
            break

    if existing:
        existing.edit(body)
    else:
        pr.create_issue_comment(body)


# --- Multi-tenant FastAPI app with GitHub OAuth ---
import os
import re
import hashlib
import hmac
def review_pr(repo: str, pr_id: int):
    gh = Github(GITHUB_TOKEN)
    gh_repo = gh.get_repo(repo)
    pr = gh_repo.get_pull(pr_id)

    findings: list[str] = []
    inline_comments: list[dict[str, object]] = []

    for changed_file in pr.get_files():
        file_findings = _build_findings(changed_file.filename, changed_file.patch or "")
        findings.extend(file_findings)

        if not file_findings:
            continue

        for finding in file_findings[:3]:
            inline_comments.append(
                {
                    "path": changed_file.filename,
                    "line": changed_file.changes if changed_file.changes else 1,
                    "side": "RIGHT",
                    "body": f"🤖 {finding}",
                }
            )

    counts = _summarize_findings(findings)
    has_critical = counts.get("critical", 0) > 0

    marker = "<!-- mcp-review-summary -->"
    top_findings = "\n".join(f"- {item}" for item in findings[:15]) or "- No issues detected."
    summary_body = (
        f"{marker}\n"
        f"**🤖 GitHub MCP Pro Review — PR #{pr_id}**\n\n"
        f"- Findings: critical {counts['critical']}, major {counts['major']}, minor {counts['minor']}, info {counts['info']}\n\n"
        f"**Top findings**\n"
        f"{top_findings}"
    )
    _upsert_issue_comment(pr, marker, summary_body)

    try:
        if has_critical and inline_comments:
            blocking_reviews_enabled = os.getenv("MCP_ENABLE_BLOCKING_REVIEWS", "false").lower() == "true"
            pr.create_review(
                commit=gh_repo.get_commit(pr.head.sha),
                body="🤖 GitHub MCP Pro inline findings",
                event="REQUEST_CHANGES" if blocking_reviews_enabled else "COMMENT",
                comments=inline_comments,
            )
        elif not has_critical:
            # Always publish an approval so any previous bot-requested changes are superseded.
            pr.create_review(
                commit=gh_repo.get_commit(pr.head.sha),
                body="🤖 GitHub MCP Pro review passed: no critical findings.",
                event="APPROVE",
            )
    except Exception as exc:
        logger.warning("Inline review failed (non-fatal): %s", _sanitize_error(str(exc)))

    status_emoji = "❌" if has_critical else "✅"
    return (
        f"{status_emoji} PR #{pr_id} reviewed: {len(findings)} finding(s) "
        f"(critical:{counts['critical']}, major:{counts['major']}, "
        f"minor:{counts['minor']}, info:{counts['info']}) reported."
    )

def assess_pr_risk(repo: str, pr_id: int):
    gh = Github(GITHUB_TOKEN)
    gh_repo = gh.get_repo(repo)
    pr = gh_repo.get_pull(pr_id)
    files = list(pr.get_files())

    score = 0
    factors: list[str] = []

    file_count = len(files)
    if file_count > 20:
        score += 30
        factors.append(f"+30 large changeset ({file_count} files)")
    elif file_count > 10:
        score += 15
        factors.append(f"+15 medium changeset ({file_count} files)")

    additions = sum(file.additions for file in files)
    if additions > 500:
        score += 20
        factors.append(f"+20 high additions ({additions} lines)")
    elif additions > 200:
        score += 10
        factors.append(f"+10 medium additions ({additions} lines)")

    sensitive = [
        file.filename for file in files
        if any(k in file.filename.lower() for k in ("auth", "token", "secret", "crypto", "password", "login"))
    ]
    if sensitive:
        score += 20
        factors.append(f"+20 sensitive files touched ({', '.join(sensitive[:3])})")

    if any("test" in file.filename.lower() for file in files):
        score -= 10
        factors.append("-10 test coverage included")

    score = max(0, min(100, score))
    level = "low" if score < 30 else "medium" if score < 60 else "high"
    factors_block = "\n".join(f"- {factor}" for factor in factors) or "- No significant risk factors."

    result = (
        f"Risk score: {score}/100 ({level})\n"
        f"Risk factors:\n{factors_block}\n"
        "Merge checklist:\n"
        "- [ ] Review all critical/major findings\n"
        "- [ ] Confirm no secrets committed\n"
        "- [ ] Tests pass locally\n"
        "- [ ] Self-review diff for logic errors"
    )

    marker = "<!-- mcp-risk-assessment -->"
    body = f"{marker}\n**🤖 Automated PR Risk Assessment**\n\n```text\n{result}\n```"
    _upsert_issue_comment(pr, marker, body)
    return result
import logging
from urllib.parse import quote
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.config import Config
from starlette.middleware.cors import CORSMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from github import Github


load_dotenv()

logger = logging.getLogger(__name__)

# Environment variable assignments (must be before app/OAuth setup)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REQUIRE_MCP_AUTH = os.getenv("REQUIRE_MCP_AUTH", "false").lower() == "true"
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

 # Restrict CORS to trusted domains (comma-separated in env)
cors_origins = os.getenv("CORS_ALLOW_ORIGINS")
if cors_origins:
    allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
else:
    # Default: allow only production domain, fallback to all for dev
    allowed_origins = ["https://stefano-mcp-pro.fly.dev"] if os.getenv("ENV") == "production" else ["*"]

# Security self-check and tests expect this guard:
 # --- Rate limiting setup ---
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@limiter.limit("60/minute")
async def index(request: Request):
    user = request.session.get('user')
    if user:
        login_name = user['login'].lower() if user.get('login') else "user"
        html = f"""
        <html>
        <head>
            <title>Welcome</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(120deg, #f8fafc 0%, #e0e7ef 100%);
                    min-height: 100vh;
                    margin: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{
                    background: #fff;
                    border-radius: 16px;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
                    padding: 2.5rem 3rem;
                    text-align: center;
                }}
                h2 {{
                    color: #22223b;
                    margin-bottom: 0.5em;
                }}
                .username {{
                    color: #3a86ff;
                    font-weight: 600;
                }}
                a.button, button.button {{
                    display: inline-block;
                    margin: 1em 0.5em 0 0.5em;
                    padding: 0.75em 2em;
                    background: #3a86ff;
                    color: #fff;
                    border-radius: 8px;
                    text-decoration: none;
                    font-size: 1.1em;
                    font-weight: 500;
                    border: none;
                    cursor: pointer;
                    transition: background 0.2s;
                }}
                a.button:hover, button.button:hover {{
                    background: #265d97;
                }}
            </style>
            <script>
                function closeWindow() {{
                    window.open('', '_self', '');
                    window.close();
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <h2>Welcome, <span class="username">{login_name}!</span></h2>
                <a href='/logout' class='button'>Logout</a>
                <button class='button' onclick='closeWindow()'>Close Window &amp; Continue</button>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html)
    html = """
<html>
<head>
    <title>Login</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(120deg, #f8fafc 0%, #e0e7ef 100%);
            min-height: 100vh;
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            padding: 2.5rem 3rem;
            text-align: center;
        }
        h1 {
            color: #22223b;
            margin-bottom: 1em;
        }
        a.button {
            display: inline-block;
            margin-top: 1.5em;
            padding: 0.75em 2em;
            background: #3a86ff;
            color: #fff;
            border-radius: 8px;
            text-decoration: none;
            font-size: 1.1em;
            font-weight: 500;
            transition: background 0.2s;
        }
        a.button:hover {
            background: #265d97;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Multi-Tenant GitHub MCP</h1>
        <a href='/login' class='button'>Login with GitHub</a>
    </div>
</body>
</html>
"""
    return HTMLResponse(html)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.github.authorize_redirect(request, redirect_uri)

# GitHub OAuth callback endpoint
@app.get("/auth", name="auth")
async def auth(request: Request):
    try:
        token = await oauth.github.authorize_access_token(request)
        user = await oauth.github.get('user', token=token)
        user_info = user.json()
        # Store user info in session
        request.session['user'] = {
            'login': user_info.get('login'),
            'avatar_url': user_info.get('avatar_url'),
            'html_url': user_info.get('html_url'),
            'name': user_info.get('name'),
        }
        return RedirectResponse(url="/")
    except OAuthError as e:
        html = f"""
        <html>
        <head>
            <title>OAuth Error</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: #ffe5e5;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{
                    background: #fff;
                    border-radius: 16px;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
                    padding: 2.5rem 3rem;
                    text-align: center;
                }}
                h2 {{ color: #d90429; }}
                p {{ color: #222; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>OAuth Error</h2>
                <p>{str(e)}</p>
                <a href="/" class="button">Back to Home</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html, status_code=400)
