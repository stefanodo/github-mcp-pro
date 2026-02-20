# Multi-Tenant GitHub OAuth FastAPI App

## Setup
1. Copy `.env.example` to `.env` and fill in:
   - `GITHUB_CLIENT_ID` (from your GitHub OAuth app)
   - `GITHUB_CLIENT_SECRET` (from your GitHub OAuth app)
   - `SECRET_KEY` (any random string)
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the app:
   ```sh
   uvicorn main:app --reload
   ```

## Usage
- Visit `/` to login with GitHub.
- After login, you can access `/my_repos` to see your repositories.
- Each user is isolated and uses their own GitHub access token.

## Notes
- This app is now multi-tenant: each user logs in with their own GitHub account and can access their own repositories securely.
- No global GitHub token is used.
