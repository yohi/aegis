# Security Guidelines

## Threat Detection
- **MUST**: Use `logger.error` for all security-critical events to ensure visibility in audit logs:
  - Input blocking by security shields.
  - Path traversal attempts.
  - Redaction failures.
- **Exception**: If suppressing these logs is necessary for specific operational reasons, you MUST ask the user for explicit confirmation before proceeding.

## Data Protection
- **MUST**: Ensure sensitive fields in `ReviewResult` (like `summary`) are redacted if security shields flag them.
- **MUST**: Never log raw content or findings that might contain sensitive customer data.
