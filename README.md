# GitHub MCP Pro 🚀

MCP server for GitHub workflows: automated PR reviews, repository-aware code generation, and issue triage.

## Features (v1.0 - MVP)

✅ **Smart PR Review**: Pattern detection (console.log, useEffect deps, TypeScript any)  
✅ **Issue Triage**: Auto-labeling (bug/feature/docs/priority) with keyword detection  
✅ **Code Templates**: React components, hooks, API routes generation  
🔄 **Coming Soon**: Full AI analysis with Claude integration (Plan C)
- **Live Endpoint**: [https://stefano-mcp-pro.fly.dev/mcp](https://stefano-mcp-pro.fly.dev/mcp)

## Quick Start

### Local Development
```bash
# Get GitHub token: https://github.com/settings/tokens (scopes: repo, workflow)
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_your_token_here \
  stefanodo/github-mcp-pro

# Test with inspector
npx @modelcontextprotocol/inspector http://localhost:8000
```

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github-pro": {
      "url": "https://stefano-mcp-pro.fly.dev/mcp",
      "transport": "http"
    }
  }
}
```

## Available Tools

### `review_pr`

Reviews pull requests and returns concrete suggestions based on changed files.

```python
review_pr(repo="owner/repo", pr_id=123)
# Returns: "✅ PR #123 reviewed: 5 files changed. Suggestions: Refactor hooks; add tests."
```

### `generate_code`

Generates code changes using repository context.

```python
generate_code(repo="owner/repo", path="src/App.js", prompt="Create login form")
# Returns: Generated React component with validation
```

### `triage_issue`

Triages GitHub issues and proposes routing metadata.

```python
triage_issue(repo="owner/repo", issue_id=45)
# Returns: "Issue #45 triaged: labeled 'bug', assigned to frontend team"
```

## Tech Stack

- Framework: FastMCP (Python 3.11)
- API: PyGithub
- Deploy: Fly.io (Paris region)
- Protocol: MCP 2025-09-29 spec

## Pricing

- Free tier: Core features with rate limits
- Pro: €9/month - Unlimited calls, multi-org support, priority support

## Development

```bash
# Clone
git clone https://github.com/stefanodo/github-mcp-pro
cd github-mcp-pro

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run
python main.py
```

## Deploy Your Own

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Deploy
flyctl launch --no-deploy
flyctl secrets set GITHUB_TOKEN=ghp_xxx
flyctl deploy
```

## License

MIT - See [LICENSE](https://github.com/stefanodo/github-mcp-pro/blob/main/LICENSE)

## Support

- Issues: [GitHub Issues](https://github.com/stefanodo/github-mcp-pro/issues)
- MCP Registry: Coming soon
- MCPMarket: Pending approval

If this project helps your workflow, consider starring the repo.