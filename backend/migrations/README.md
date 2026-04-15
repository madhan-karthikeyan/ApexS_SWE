# Alembic Migrations

This folder stores schema migration scripts for the backend database.

## Common commands

Run from the backend folder.

- Create migration:
  - `alembic revision --autogenerate -m "describe_change"`
- Apply latest migrations:
  - `alembic upgrade head`
- Roll back one step:
  - `alembic downgrade -1`
- Show current revision:
  - `alembic current`

## Notes

- `env.py` imports `app.models` so SQLAlchemy metadata includes all models.
- Database URL is sourced from `app.core.config.settings.database_url`.
