# MCP Smoke Test

Quick validation checklist for `github-pro`.

## Branching Policy (Required)

- Never commit directly to `main`.
- Create a branch for every change.
- Open a Pull Request to `main`.
- Merge only after PR approval.

Current repo protection on `main` enforces PR-based workflow.

## 30-Second Health Check

### 1) Initialize session

```bash
curl -i https://stefano-mcp-pro.fly.dev/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-09-29","capabilities":{},"clientInfo":{"name":"smoke-runner","version":"1.0"}}}'
```

Expected: `HTTP/2 200` and `content-type: text/event-stream`.

### 2) List tools

```bash
SID=$(curl -sD - https://stefano-mcp-pro.fly.dev/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-09-29","capabilities":{},"clientInfo":{"name":"smoke-runner","version":"1.0"}}}' \
  -o /dev/null | awk '/[Mm][Cc][Pp]-[Ss]ession-[Ii][Dd]:/ {print $2}' | tr -d '\r')

curl -sS https://stefano-mcp-pro.fly.dev/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Expected tools: `review_pr`, `generate_code`, `triage_issue`.

## Reusable Test IDs

- Smoke issue: `#3`
- Smoke PR: `#4`

## Functional Tool Calls

### Triage issue

```bash
SID=$(curl -sD - https://stefano-mcp-pro.fly.dev/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-09-29","capabilities":{},"clientInfo":{"name":"smoke-runner","version":"1.0"}}}' \
  -o /dev/null | awk '/[Mm][Cc][Pp]-[Ss]ession-[Ii][Dd]:/ {print $2}' | tr -d '\r')

curl -sS https://stefano-mcp-pro.fly.dev/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":30,"method":"tools/call","params":{"name":"triage_issue","arguments":{"repo":"stefanodo/github-mcp-pro","issue_id":3}}}'
```

### Review PR

```bash
SID=$(curl -sD - https://stefano-mcp-pro.fly.dev/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-09-29","capabilities":{},"clientInfo":{"name":"smoke-runner","version":"1.0"}}}' \
  -o /dev/null | awk '/[Mm][Cc][Pp]-[Ss]ession-[Ii][Dd]:/ {print $2}' | tr -d '\r')

curl -sS https://stefano-mcp-pro.fly.dev/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":31,"method":"tools/call","params":{"name":"review_pr","arguments":{"repo":"stefanodo/github-mcp-pro","pr_id":4}}}'
```
