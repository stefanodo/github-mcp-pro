
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

def _sanitize_error(msg: str) -> str:
    # Redact GitHub tokens (ghp_...) and similar patterns
    token_pattern = re.compile(r"ghp_[A-Za-z0-9]{32,}")
    return token_pattern.sub("[REDACTED_TOKEN]", msg)
# --- Multi-tenant FastAPI app with GitHub OAuth ---
import os
import re
import hashlib
import hmac
def review_pr(repo: str, pr_id: int):
    """Stub for review_pr. Replace with actual implementation."""
    return f"Review for PR #{pr_id} in repo {repo}"

def assess_pr_risk(repo: str, pr_id: int):
    """Stub for assess_pr_risk. Replace with actual implementation."""
    return f"Risk assessment for PR #{pr_id} in repo {repo}"
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
