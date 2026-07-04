# Security Policy

We take codebase safety and API credential security seriously. This policy outlines how security vulnerabilities should be reported and details our built-in safety boundaries.

---

## 🛡️ Built-in Security Safeguards

README Copilot implements two layers of automated security:
1. **Directory Exclusion Rules**: Directory scanners in our MCP server completely ignore `.git/`, `node_modules/`, and virtual environments (`venv/`, `.venv/`) during walks.
2. **Credential Read Blocks**: The MCP `read_file` tool checks target filenames. Attempts to read real `.env` settings or private keys (`.pem`, `.key`) are blocked at the code level, preventing LLMs from accessing committed secrets.

---

## 🐛 Reporting a Vulnerability

If you discover a security vulnerability (such as a directory traversal escape or prompt injection that bypasses credential blocks):

1. **Do NOT open a public issue** on GitHub.
2. Report the vulnerability privately by sending an email to `contact@example.com` containing:
   - A description of the vulnerability.
   - Step-by-step instructions or PoC code to reproduce the issue.
   - The potential impact.
3. We will review your report and coordinate a fix before publicly disclosing the issue.
