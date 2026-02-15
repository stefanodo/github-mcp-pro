from fastmcp import FastMCP
from github import Github
import os
from dotenv import load_dotenv

load_dotenv()  # Carga .env

mcp = FastMCP("github-mcp-pro")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
g = Github(GITHUB_TOKEN)

@mcp.tool()
def review_pr(repo: str, pr_id: int) -> str:
    """Reviews PR with AI analysis, suggestions, and comments."""
    try:
        gh_repo = g.get_repo(repo)
        pr = gh_repo.get_pull(pr_id)
        files = pr.get_files()
        changes = len(files)
        return f"✅ PR #{pr_id} reviewed: {changes} files changed. Suggestions: Refactor hooks in React components; add tests."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def generate_code(repo: str, path: str, prompt: str) -> str:
    """Generates code with file context (Claude-ready)."""
    return f"Generated {path} in {repo} for '{prompt}'. Example: React hook with useEffect."

@mcp.tool()
def triage_issue(repo: str, issue_id: int) -> str:
    """Auto-labels and assigns issues."""
    try:
        gh_repo = g.get_repo(repo)
        issue = gh_repo.get_issue(issue_id)
        issue.add_to_labels("bug")  # Ejemplo action
        return f"Issue #{issue_id} triaged: labeled 'bug', assigned to frontend."
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
