# EVD API

## Database

Visist [https://chartdb.byandrev.dev](https://chartdb.byandrev.dev) and import the file `db.json` to view the database schema. If you make changes, export the JSON file and update it in the repository

## Instructions

1. `python -m venv venv`
2. `source venv/bin/activate`
3. `python -m pip install -r requirements.txt`
4. `fastapi dev api/app.py`

## Docker Compose

### Dev

1. `docker compose -f docker-compose.dev.yaml up`
2. `docker compose -f docker-compose.dev.yaml down`

### Prod

1. `docker compose -f docker-compose.yaml up`
2. `docker compose -f docker-compose.yaml down`

## Migration

- For migration instructions and the recommended workflow, see [MIGRATIONS.md](MIGRATIONS.md).

## Seeding (roles + admin)

1. Run migrations first:
   - `alembic upgrade head`
2. Set required env vars:
   - `SEED_ADMIN_UID`
   - `SEED_ADMIN_EMAIL`
3. (Optional) Set:
   - `SEED_ADMIN_USERNAME`
   - `SEED_ADMIN_NAME`
   - `SEED_ADMIN_AVATAR_URL`
   - `SEED_ADMIN_DEPARTMENT_ID`
   - `SEED_ADMIN_ROLES` (comma-separated, default `ADMIN`)
4. Run seed script:
   - `python scripts/seed_roles_admin.py`
