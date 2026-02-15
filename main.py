from fastmcp import FastMCP
from github import Github, Auth
import os
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
        
        # Analyze each file
        for file in files:
            if not file.patch:
                continue
                
            patch = file.patch.lower()
            filename = file.filename
            
            # Pattern detection (regex smart)
            if filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
                if 'console.log' in patch:
                    issues_found.append(f"⚠️ {filename}: Remove console.log before merge")
                if 'useeffect' in patch and 'dependency' not in patch:
                    issues_found.append(f"⚠️ {filename}: Check useEffect dependencies")
                if 'any' in patch and '.ts' in filename:
                    issues_found.append(f"💡 {filename}: Avoid 'any' type, use specific types")
            
            if '+import' in patch and filename.count('/') > 3:
                issues_found.append(f"💡 {filename}: Deep imports detected, consider barrel exports")
        
        # Generate review summary
        summary = f"**🤖 GitHub MCP Pro Review - PR #{pr_id}**\n\n"
        summary += f"📊 **Stats**: {len(files)} files, {pr.additions} additions, {pr.deletions} deletions\n\n"
        
        if issues_found:
            summary += "**Issues & Suggestions**:\n" + "\n".join([f"- {issue}" for issue in issues_found[:10]])
        else:
            summary += "✅ No common issues detected. Code looks clean!"
        
        summary += f"\n\n---\n*Automated by GitHub MCP Pro*"
        
        # Post comment
        pr.create_issue_comment(summary)
        
        return f"✅ PR #{pr_id} reviewed: {len(files)} files analyzed, {len(issues_found)} suggestions posted."
        
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

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
