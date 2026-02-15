# GitHub MCP Pro 🚀

MCP server for GitHub workflows: automated PR reviews, repository-aware code generation, and issue triage.

## Features

✅ **Smart PR Review**: Finds actionable issues in changed code and posts a PR summary comment  
✅ **Lint-Style Findings**: `critical/major/minor/info` severity buckets with per-finding details  
✅ **Clickable Code Links**: Findings include direct GitHub links to file + exact line  
✅ **Inline PR Annotations**: Lint findings are also posted as inline comments in `Files changed`  
✅ **PR Risk Scoring**: Risk score (0-100), level, and merge checklist for each PR  
✅ **Issue Triage**: Auto-labeling (bug/feature/docs/priority) with keyword detection  
✅ **Code Templates**: React components, hooks, API routes generation  
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

Reviews pull requests, posts a summary comment, and creates inline lint annotations.

```python
review_pr(repo="owner/repo", pr_id=123)
# Returns: "✅ PR #123 reviewed: ... suggestions and ... lint findings reported (... inline comments created)."
```

Natural-language prompt example:

```text
Review PR 123 in owner/repo with github-pro.
```

### `generate_code`

Generates code changes using repository context.

```python
generate_code(repo="owner/repo", path="src/App.js", prompt="Create login form")
# Returns: Generated React component with validation
```

Natural-language prompt example:

```text
With github-pro, generate code for owner/repo at src/App.js to create a login form with validation.
```

### `triage_issue`

Triages GitHub issues and proposes routing metadata.

```python
triage_issue(repo="owner/repo", issue_id=45)
# Returns: "Issue #45 triaged: labeled 'bug', assigned to frontend team"
```

Natural-language prompt example:

```text
Triage issue 45 in owner/repo using github-pro.
```

### `assess_pr_risk`

Scores pull request risk and returns an actionable review checklist (chat-side output).

```python
assess_pr_risk(repo="owner/repo", pr_id=123)
# Returns: "Risk score: 62/100 (high), key risk factors, and merge checklist"
```

Natural-language prompt example:

```text
Assess risk for PR 123 in owner/repo with github-pro.
```

## End-to-End Natural Language Examples (No curl)

Use these prompts directly in your chat client with MCP enabled:

```text
With github-pro, review PR 123 in owner/repo and then assess the PR risk.
```

```text
In owner/repo, triage issue 45 and then review PR 123 with github-pro.
```

```text
Use github-pro to generate a React login component at src/components/Login.tsx in owner/repo, then review PR 123 and evaluate its risk.
```

```text
Run the full flow with github-pro for owner/repo: triage issue 45, review PR 123, and assess PR risk.
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

## Smoke Testing

- Use [SMOKE_TEST.md](SMOKE_TEST.md) for copy/paste checks of `initialize`, `tools/list`, `triage_issue`, and `review_pr`.

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