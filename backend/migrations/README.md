# Alembic Migrations

This directory belongs to the rebuilt PostgreSQL architecture.

Common commands from `backend/`:

```bash
alembic revision --autogenerate -m "create initial tables"
alembic upgrade head
```

The old SQLite demo migration helpers remain in `backend/app/database.py` until the new models replace them.
