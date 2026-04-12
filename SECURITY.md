# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please:

1. **DO NOT** open a public issue
2. Email the maintainers directly at [your-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will:
- Acknowledge receipt within 48 hours
- Provide a timeline for a fix within 7 days
- Credit you in the release notes (unless you prefer to remain anonymous)

## Security Considerations

This tool:
- Only reads your code (never modifies)
- Stores data locally in `.code_graph.db`
- Does not send code to external servers
- Works offline after installation
