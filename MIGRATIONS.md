# Migrations (FastAPI + Alembic)

This document describes a minimal, safe workflow for schema migrations when using FastAPI with SQLAlchemy and Alembic.

## Add model

1. Add the model to your SQLAlchemy models in code.
2. Import the model in `alembic/env.py`.
3. Generate a migration script (autogenerate):
   - `alembic revision --autogenerate -m "add project table"`
   - Inspect the generated migration file in `migrations/versions/`.
4. Apply the migration to the database:
   - `alembic upgrade head`

## Typical workflow

1. Change your SQLAlchemy models in code.
2. Generate a migration script (autogenerate):
   - `alembic revision --autogenerate -m "add project table"`
   - Inspect the generated migration file in `migrations/versions/` and edit if needed.
3. Apply the migration to the database:
   - `alembic upgrade head`
4. (Optional) Apply to a single revision:
   - `alembic upgrade <revision_id>`
5. Rollback / downgrade:
   - `alembic downgrade -1` (one step)
   - `alembic downgrade <revision_id>` (to a specific revision)
6. Other useful commands:
   - `alembic current` — show current DB revision
   - `alembic history --verbose` — list revision history
   - `alembic stamp head` — mark DB as up-to-date without running migrations

## Example minimal commands
- Create revision: `alembic revision --autogenerate -m "create projects table"`
- Apply all: `alembic upgrade head`
- Revert last: `alembic downgrade -1`

## Links / Docs
- Alembic docs: https://alembic.sqlalchemy.org/en/latest/
- FastAPI — SQL (Databases) tutorial: https://fastapi.tiangolo.com/tutorial/sql-databases/
- SQLAlchemy migrations (overview): https://docs.sqlalchemy.org/en/latest/core/metadata.html
