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

# Tests

Este directorio contiene los tests automatizados del proyecto.

## Estructura

```
tests/
├── conftest.py                 # Fixtures compartidos
├── unit/                       # Tests unitarios (mocks)
│   ├── repositories/           # Tests de la capa de repositorios
│   │   └── test_users_repository.py
│   ├── services/               # Tests de la capa de servicios
│   │   └── test_user_service.py
│   ├── controllers/            # Tests de la capa de controladores
│   │   └── test_users_controller.py
│   ├── test_middleware.py      # Tests del middleware de envelope
│   └── test_exceptions.py     # Tests de los exception handlers
└── integration/                # Tests de integración (requieren DB)
    └── test_users_routes.py    # Tests de rutas HTTP
```

## Tests

```bash
# Ejecutar todos los tests
pytest

# Ejecutar con verbose
pytest -v

# Ejecutar solo tests unitarios
pytest tests/unit/

# Ejecutar solo tests de integración
pytest tests/integration/

# Ejecutar un archivo específico
pytest tests/unit/services/test_user_service.py

# Ejecutar con coverage
pytest --cov=api --cov-report=html
```

## Notas

- Los tests de integración con autenticación están skippeados porque requieren una DB real
- Para tests de integración completos, se recomienda usar pytest-postgresql o testcontainers
- Los tests unitarios mockean todas las dependencias externas