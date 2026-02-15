from fastmcp import FastMCP
from github import Github, Auth
import os
import re
import hashlib
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("github-mcp-pro")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

@mcp.tool()
def review_pr(repo: str, pr_id: int) -> str:
    """Reviews PR: analyzes diff, detects issues, posts suggestions."""
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        gh_repo = g.get_repo(repo)
        pr = gh_repo.get_pull(pr_id)
        
        files = list(pr.get_files())
        issues_found = []
        lint_findings = []
        lint_seen = set()
        pr_blob_base = f"https://github.com/{repo}/blob/{pr.head.sha}"

        def build_inline_marker(finding: dict) -> str:
            marker_seed = f"{finding['severity']}|{finding['filename']}|{finding['line']}|{finding['message']}"
            marker_hash = hashlib.sha1(marker_seed.encode()).hexdigest()[:12]
            return f"mcp-lint:{marker_hash}"

        def extract_added_lines_with_numbers(patch_text: str):
            added = []
            current_new_line = None

            for raw in patch_text.splitlines():
                if raw.startswith('@@'):
                    hunk_match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
                    if hunk_match:
                        current_new_line = int(hunk_match.group(1))
                    continue

                if current_new_line is None:
                    continue

                if raw.startswith('+++') or raw.startswith('---'):
                    continue

                if raw.startswith('+'):
                    added.append((current_new_line, raw[1:]))
                    current_new_line += 1
                elif raw.startswith('-'):
                    continue
                else:
                    current_new_line += 1

            return added

        def add_lint(severity: str, filename: str, line_number: int, message: str):
            key = (severity.upper(), filename, line_number, message)
            if key in lint_seen:
                return
            lint_seen.add(key)

            safe_path = quote(filename, safe='/')
            if line_number:
                link = f"[{filename}:{line_number}]({pr_blob_base}/{safe_path}#L{line_number})"
            else:
                link = f"[{filename}]({pr_blob_base}/{safe_path})"

            lint_findings.append({
                "severity": severity.upper(),
                "message": message,
                "filename": filename,
                "line": line_number,
                "link": link,
            })
        
        # Analyze each file
        for file in files:
            if not file.patch:
                continue
                
            patch = file.patch.lower()
            filename = file.filename
            added_lines_with_numbers = extract_added_lines_with_numbers(file.patch)
            added_lines = [line_text for _, line_text in added_lines_with_numbers]
            added_text = "\n".join(added_lines).lower()
            comment_lines = [
                (line_number, line_text) for line_number, line_text in added_lines_with_numbers
                if line_text.strip().startswith(('#', '//', '/*', '*'))
            ]
            code_lines = [
                (line_number, line_text) for line_number, line_text in added_lines_with_numbers
                if line_text.strip() and not line_text.strip().startswith(('#', '//', '/*', '*'))
            ]
            
            # Pattern detection (regex smart)
            if filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
                if 'console.log' in added_text:
                    issues_found.append(f"⚠️ {filename}: Remove console.log before merge")
                    for line_number, line_text in code_lines:
                        if 'console.log' in line_text.lower():
                            add_lint("minor", filename, line_number, "debug statement (console.log) added")
                for line_number, line_text in code_lines:
                    if re.search(r"(?<!['\"])\bdebugger\b", line_text):
                        add_lint("major", filename, line_number, "debugger statement added")
                    if re.search(r"^\s*var\s+", line_text):
                        add_lint("minor", filename, line_number, "use let/const instead of var")
                for line_number, line_text in added_lines_with_numbers:
                    if 'eslint-disable' in line_text.lower():
                        add_lint("major", filename, line_number, "eslint-disable directive added")
                if 'useeffect' in added_text and 'dependency' not in added_text:
                    issues_found.append(f"⚠️ {filename}: Check useEffect dependencies")
                if 'any' in added_text and '.ts' in filename:
                    issues_found.append(f"💡 {filename}: Avoid 'any' type, use specific types")
                    for line_number, line_text in code_lines:
                        if re.search(r"\bany\b", line_text):
                            add_lint("major", filename, line_number, "TypeScript 'any' introduced")

            if filename.endswith('.py'):
                for line_number, line_text in code_lines:
                    if re.search(r"^\s*except\s*:\s*$", line_text):
                        add_lint("major", filename, line_number, "bare except detected")
                if '/test' not in filename.lower() and '/tests' not in filename.lower():
                    for line_number, line_text in code_lines:
                        if re.search(r"(?<!['\"])\bprint\s*\(", line_text):
                            add_lint("info", filename, line_number, "print() added outside tests")

            for line_number, line_text in code_lines:
                if re.search(r"(?<!['\"])\beval\s*\(", line_text):
                    add_lint("critical", filename, line_number, "eval usage detected")

            secret_assignment_regex = re.compile(
                r"^\s*(?:const\s+|let\s+|var\s+)?[A-Za-z_][A-Za-z0-9_]*(?:password|secret|api[_-]?key|token)[A-Za-z0-9_]*\s*=\s*['\"][^'\"]{4,}['\"]",
                re.IGNORECASE,
            )
            token_literal_regex = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
            for line_number, line_text in code_lines:
                if secret_assignment_regex.search(line_text) or token_literal_regex.search(line_text):
                    add_lint("critical", filename, line_number, "potential hardcoded secret pattern")

            for line_number, line_text in comment_lines:
                if re.search(r"\b(todo|fixme)\b", line_text, flags=re.IGNORECASE):
                    add_lint("info", filename, line_number, "TODO/FIXME added")
            
            if '+import' in patch and filename.count('/') > 3:
                issues_found.append(f"💡 {filename}: Deep imports detected, consider barrel exports")

        # Lightweight risk summary for quick merge prioritization
        total_changes = pr.additions + pr.deletions
        risk_score = 0

        if len(files) > 15:
            risk_score += 18
        elif len(files) > 8:
            risk_score += 10

        if total_changes > 800:
            risk_score += 18
        elif total_changes > 300:
            risk_score += 10

        sensitive_terms = [
            'auth', 'security', 'permission', 'role', 'token', 'secret',
            'billing', 'payment', 'database', 'schema', 'migration',
            'deploy', 'infra', 'config', 'middleware', 'crypto'
        ]
        sensitive_touches = 0
        test_files = 0

        for file in files:
            filename = file.filename.lower()
            if any(term in filename for term in sensitive_terms):
                sensitive_touches += 1

            if (
                '/test' in filename
                or '/tests' in filename
                or filename.endswith('.test.js')
                or filename.endswith('.test.ts')
                or filename.endswith('.spec.js')
                or filename.endswith('.spec.ts')
                or filename.startswith('test_')
            ):
                test_files += 1

        if sensitive_touches:
            risk_score += min(24, 8 + (sensitive_touches * 4))
        if len(files) - test_files > 0 and test_files == 0:
            risk_score += 12

        risk_score = min(100, risk_score)
        if risk_score >= 70:
            risk_level = "critical"
        elif risk_score >= 45:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate review summary
        summary = f"**🤖 GitHub MCP Pro Review - PR #{pr_id}**\n\n"
        summary += f"📊 **Stats**: {len(files)} files, {pr.additions} additions, {pr.deletions} deletions\n"
        summary += f"🚦 **Risk**: {risk_score}/100 ({risk_level})\n\n"

        if lint_findings:
            severity_order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3}
            lint_findings.sort(
                key=lambda item: (
                    severity_order.get(item["severity"], 99),
                    item["filename"],
                    item["line"],
                )
            )
            lint_counts = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0}
            for finding in lint_findings:
                if finding["severity"] in lint_counts:
                    lint_counts[finding["severity"]] += 1

            summary += (
                "🧹 **Lint Findings**: "
                f"critical {lint_counts['CRITICAL']}, "
                f"major {lint_counts['MAJOR']}, "
                f"minor {lint_counts['MINOR']}, "
                f"info {lint_counts['INFO']}\n"
            )
            summary += "\n**Top Lint Alerts**:\n"
            for finding in lint_findings[:8]:
                summary += f"- {finding['severity']}: {finding['message']} at {finding['link']}\n"
            summary += "\n"
        
        if issues_found:
            summary += "**Issues & Suggestions**:\n" + "\n".join([f"- {issue}" for issue in issues_found[:10]])
        elif not lint_findings:
            summary += "✅ No common issues detected. Code looks clean!"
        
        summary += f"\n\n---\n*Automated by GitHub MCP Pro*"

        inline_posted = 0
        try:
            existing_markers = set()
            for review_comment in pr.get_review_comments():
                body = review_comment.body or ""
                for match in re.findall(r"mcp-lint:[a-f0-9]{12}", body):
                    existing_markers.add(match)

            for finding in lint_findings:
                if finding["severity"] not in {"CRITICAL", "MAJOR"}:
                    continue
                if not finding.get("line"):
                    continue

                marker = build_inline_marker(finding)
                if marker in existing_markers:
                    continue

                inline_body = (
                    f"🧹 **MCP Lint {finding['severity']}**\n"
                    f"{finding['message']}\n"
                    f"Source: {finding['link']}\n"
                    f"<!-- {marker} -->"
                )

                try:
                    pr.create_review_comment(
                        body=inline_body,
                        commit=pr.head.sha,
                        path=finding["filename"],
                        line=finding["line"],
                        side="RIGHT",
                    )
                    inline_posted += 1
                    existing_markers.add(marker)
                except Exception:
                    continue
        except Exception:
            inline_posted = 0
        
        # Post comment
        pr.create_issue_comment(summary)
        
        return (
            f"✅ PR #{pr_id} reviewed: {len(files)} files analyzed, "
            f"{len(issues_found)} suggestions and {len(lint_findings)} lint findings reported "
            f"({inline_posted} inline comments created)."
        )
        
    except Exception as e:
        return f"❌ Error reviewing PR: {str(e)}"

@mcp.tool()
def generate_code(repo: str, path: str, prompt: str) -> str:
    """Generates code from templates based on prompt keywords."""
    try:
        code = ""
        prompt_lower = prompt.lower()
        
        # React component templates
        if 'component' in prompt_lower or 'react' in prompt_lower:
            comp_name = path.split('/')[-1].replace('.tsx', '').replace('.jsx', '').replace('.js', '')
            code = f"""import React from 'react';

interface {comp_name}Props {{
  // Add props here
}}

export const {comp_name}: React.FC<{comp_name}Props> = (props) => {{
  return (
    <div className="{comp_name.lower()}">
      <h2>{comp_name}</h2>
      {{/* Component content */}}
    </div>
  );
}};
"""
        
        # Hook template
        elif 'hook' in prompt_lower:
            hook_name = path.split('/')[-1].replace('.ts', '').replace('.js', '')
            code = f"""import {{ useState, useEffect }} from 'react';

export const {hook_name} = () => {{
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {{
    // Hook logic here
  }}, []);
  
  return {{ data, loading }};
}};
"""
        
        # API route
        elif 'api' in prompt_lower or 'endpoint' in prompt_lower:
            code = f"""export async function GET(request: Request) {{
  try {{
    // API logic
    return Response.json({{ success: true }});
  }} catch (error) {{
    return Response.json({{ error: error.message }}, {{ status: 500 }});
  }}
}}
"""
        
        else:
            return f"❌ Unknown template for: '{prompt}'. Supported: component, hook, api"
        
        return f"✅ Generated {path}:\n```typescript\n{code}\n```\n\n💡 Copy code and create file manually, or integrate with repo write access."
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@mcp.tool()
def triage_issue(repo: str, issue_id: int) -> str:
    """Smart triage: auto-labels, detects type/priority, assigns."""
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        gh_repo = g.get_repo(repo)
        issue = gh_repo.get_issue(issue_id)
        
        text = f"{issue.title} {issue.body or ''}".lower()
        labels_to_add = []
        
        # Type detection
        bug_keywords = ['bug', 'error', 'crash', 'broken', 'fail', 'not working', 'issue']
        feature_keywords = ['feature', 'add', 'new', 'implement', 'support', 'request']
        docs_keywords = ['doc', 'documentation', 'readme', 'guide', 'example']
        
        if any(kw in text for kw in bug_keywords):
            labels_to_add.append('bug')
        elif any(kw in text for kw in feature_keywords):
            labels_to_add.append('enhancement')
        elif any(kw in text for kw in docs_keywords):
            labels_to_add.append('documentation')
        
        # Priority detection
        high_priority = ['urgent', 'critical', 'asap', 'production', 'security']
        if any(kw in text for kw in high_priority):
            labels_to_add.append('priority:high')
        
        # Frontend/Backend detection
        if any(kw in text for kw in ['react', 'component', 'ui', 'css', 'frontend']):
            labels_to_add.append('frontend')
        if any(kw in text for kw in ['api', 'backend', 'database', 'server']):
            labels_to_add.append('backend')
        
        # Apply labels (create if not exist)
        existing_labels = [l.name for l in gh_repo.get_labels()]
        for label in labels_to_add:
            if label not in existing_labels:
                colors = {
                    'bug': 'd73a4a',
                    'enhancement': 'a2eeef',
                    'documentation': '0075ca',
                    'priority:high': 'd93f0b',
                    'frontend': 'fbca04',
                    'backend': '1d76db'
                }
                gh_repo.create_label(label, colors.get(label, 'ededed'))
            
            issue.add_to_labels(label)
        
        result = f"✅ Issue #{issue_id} triaged:\n"
        result += f"- Labels: {', '.join(labels_to_add) if labels_to_add else 'none'}\n"
        result += f"- Type: {labels_to_add[0] if labels_to_add else 'general'}"
        
        return result
        
    except Exception as e:
        return f"❌ Error triaging issue: {str(e)}"

@mcp.tool()
def assess_pr_risk(repo: str, pr_id: int) -> str:
    """Assesses PR risk score with actionable review checklist."""
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        gh_repo = g.get_repo(repo)
        pr = gh_repo.get_pull(pr_id)

        files = list(pr.get_files())
        total_changes = pr.additions + pr.deletions
        risk_score = 0
        risk_factors = []

        if len(files) > 15:
            risk_score += 18
            risk_factors.append(f"Large PR footprint: {len(files)} files changed")
        elif len(files) > 8:
            risk_score += 10
            risk_factors.append(f"Medium-large PR: {len(files)} files changed")

        if total_changes > 800:
            risk_score += 18
            risk_factors.append(f"High code churn: {total_changes} lines changed")
        elif total_changes > 300:
            risk_score += 10
            risk_factors.append(f"Moderate code churn: {total_changes} lines changed")

        sensitive_terms = [
            'auth', 'security', 'permission', 'role', 'token', 'secret',
            'billing', 'payment', 'database', 'schema', 'migration',
            'deploy', 'infra', 'config', 'middleware', 'crypto'
        ]

        sensitive_files = []
        test_files = 0
        risky_signals = 0

        for changed_file in files:
            filename = changed_file.filename.lower()
            patch = (changed_file.patch or '').lower()

            if any(term in filename for term in sensitive_terms):
                sensitive_files.append(changed_file.filename)

            if (
                '/test' in filename
                or '/tests' in filename
                or filename.endswith('.test.js')
                or filename.endswith('.test.ts')
                or filename.endswith('.spec.js')
                or filename.endswith('.spec.ts')
                or filename.startswith('test_')
            ):
                test_files += 1

            signal_map = {
                'eval(': 'Dynamic evaluation detected (eval)',
                'innerhtml': 'Potential XSS surface (innerHTML)',
                'dangerouslysetinnerhtml': 'Potential XSS surface (dangerouslySetInnerHTML)',
                'os.system(': 'Shell execution detected (os.system)',
                'subprocess.': 'Process execution detected (subprocess)',
                'drop table': 'Destructive SQL statement in patch',
                'alter table': 'Schema mutation in patch',
                'chmod 777': 'Overly permissive file mode',
                'skip(ci)': 'CI skip marker detected'
            }

            for pattern, message in signal_map.items():
                if pattern in patch:
                    risky_signals += 1
                    if message not in risk_factors:
                        risk_factors.append(message)

        if sensitive_files:
            sensitive_bonus = min(24, 8 + (len(sensitive_files) * 4))
            risk_score += sensitive_bonus
            risk_factors.append(
                f"Sensitive surface touched: {len(sensitive_files)} file(s)"
            )

        if risky_signals:
            risk_score += min(20, risky_signals * 4)

        non_test_files = max(0, len(files) - test_files)
        if non_test_files > 0 and test_files == 0:
            risk_score += 12
            risk_factors.append("No test files changed")

        risk_score = min(100, risk_score)

        if risk_score >= 70:
            risk_level = "critical"
        elif risk_score >= 45:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        checklist = [
            "Run full CI and verify no skipped checks",
            "Verify rollback path for this change",
            "Confirm monitoring/alerts impacted by this PR"
        ]

        if sensitive_files:
            checklist.append("Request security-focused review for sensitive files")
        if any('database' in file.lower() or 'migration' in file.lower() for file in sensitive_files):
            checklist.append("Validate migration safety and backward compatibility")
        if test_files == 0 and non_test_files > 0:
            checklist.append("Add or request tests before merge")

        report = f"✅ PR #{pr_id} Risk Assessment\n"
        report += f"- Risk score: {risk_score}/100 ({risk_level})\n"
        report += f"- Scope: {len(files)} files, {pr.additions} additions, {pr.deletions} deletions\n"
        report += f"- Test files changed: {test_files}\n"

        if risk_factors:
            report += "- Key risk factors:\n"
            for factor in risk_factors[:8]:
                report += f"  - {factor}\n"

        report += "- Recommended checklist:\n"
        for item in checklist[:6]:
            report += f"  - {item}\n"

        return report.strip()

    except Exception as e:
        return f"❌ Error assessing PR risk: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
