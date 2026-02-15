# Security Policy

## Supported Versions

This project currently supports the latest `main` branch.

## Reporting a Vulnerability

If you find a security issue, **do not open a public GitHub issue**.

Please report privately:
- Open a private security advisory in GitHub (preferred), or
- Contact the maintainer directly and include:
  - impact summary
  - reproduction steps
  - affected version/commit
  - suggested remediation (if known)

## Secret Exposure Response

If a token or API key is exposed, follow this sequence immediately:

1. Revoke the exposed credential.
2. Generate a replacement credential with minimum required scopes.
3. Update deployment secrets (`GITHUB_TOKEN`, `MCP_AUTH_TOKEN`) in your platform.
4. Rotate local `.env` values.
5. Re-deploy.
6. Review recent logs/usage for suspicious activity.

## Runtime Hardening Checklist

- Set `REQUIRE_MCP_AUTH=true` in public deployments.
- Set a strong random `MCP_AUTH_TOKEN`.
- Keep `GITHUB_TOKEN` scoped to minimum required permissions.
- Keep `HOST=0.0.0.0` only in container/platform runtime contexts.
- Keep `.env` out of version control.

## Dependency Security

- Dependency scanning is enforced via:
  - `.github/workflows/dependency-security.yml` (`pip-audit`)
  - `.github/workflows/secret-security.yml` (`gitleaks`)
  - `.github/workflows/code-security.yml` (`bandit`)
- Review and remove temporary vulnerability allowlists when fixes become available.
