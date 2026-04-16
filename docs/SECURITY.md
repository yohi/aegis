# Security Guidelines

## Threat Detection
- Use `logger.error` for all security-critical events:
  - Input blocking by security shields.
  - Path traversal attempts.
  - Redaction failures.

## Data Protection
- Ensure sensitive fields in `ReviewResult` (like `summary`) are redacted if security shields flag them.
- Never log raw content or findings that might contain sensitive customer data.
