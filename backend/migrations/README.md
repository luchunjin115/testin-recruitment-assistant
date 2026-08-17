# Alembic Migrations

This directory belongs to the rebuilt PostgreSQL architecture.

## Naming convention

All newly generated revisions use:

```text
YYYYMMDD_HHMMSS_<revision>_<action>_<object>.py
```

Example:

```text
20260817_153000_e7b1c9d4a206_add_application_foundation.py
```

Rules:

- Use lowercase English `snake_case` for the description.
- Start the description with a clear action such as `create`, `add`, `alter`,
  `drop`, `rename`, `backfill`, `migrate`, or `merge`.
- Name the actual database or business object; avoid vague descriptions such as
  `update_db`, `fix_table`, or `new_migration`.
- Treat `revision` and `down_revision` as the source of truth for execution
  order. The timestamp is for human navigation only.
- Do not modify a revision after it has been merged or applied to a shared
  database. Add a new corrective revision instead.
- Keep one revision focused on one schema concern. Include tightly coupled data
  backfills in the same revision when required for a safe schema change.
- Use `<timestamp>_<revision>_merge_heads.py` for an Alembic merge revision.

Existing revision filenames are retained because tests and historical documents
refer to them. The convention applies to all new revisions.

Common commands from `backend/`:

```bash
python -m alembic revision --autogenerate -m "add_candidate_status"
python -m alembic upgrade head
python -m alembic current
python -m alembic history
```

Stage 7 revision `e7b1c9d4a206` was verified on 2026-08-17 against an isolated
PostgreSQL 16 database with `c8 -> e7 -> c8 -> e7` and `alembic check`. JSON
backfill values use bound parameters plus `CAST(... AS jsonb)`; do not embed
serialized JSON directly in `sa.text`, because JSON colons can be interpreted
as SQLAlchemy bind markers.

The old SQLite demo migration helpers remain in `backend/app/database.py` until the new models replace them.
