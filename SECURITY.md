# Security policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a vulnerability

PersonalRAGVault is a **local CLI** — it does not expose a network service by default.

If you discover a security issue (e.g. path handling, dependency vulnerability, sensitive data leakage):

1. **Do not** open a public issue for undisclosed vulnerabilities
2. Email or message the repository owner via GitHub (private security advisory preferred):
   - Repo: https://github.com/seanebones-lang/personal-RAG
   - Use **Report a vulnerability** under Security → Advisories if available
3. Include steps to reproduce, impact, and suggested fix if you have one

We aim to acknowledge reports within 7 days.

## Security practices for users

- Run ingest only on folders you trust; the tool reads file contents
- Keep Ollama bound to localhost unless you understand the risk of exposing it
- Do not commit `.env` or personal vault data (`~/.personalragvault/`)
- Pin or audit dependencies for production deployments

## Dependencies

Security updates for Python dependencies should be proposed via pull request or reported as above. CI runs on every PR but does not replace dependency review.
