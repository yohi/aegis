# Architecture Guidelines

## Microkernel & Protocol-first Design
- Core logic in `src/core` depends only on protocols defined in `src/core/protocols.py`.
- Avoid direct dependencies on concrete implementation classes from the core.

## Logging & Auditing
- Use `structlog` for all structured logging.
- Record **state transitions** (e.g., `pending` -> `in_progress`) as audit events at major process milestones.
- Ensure `request_id` and `actor` are included in state transition logs.
