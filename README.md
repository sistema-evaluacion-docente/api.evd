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
