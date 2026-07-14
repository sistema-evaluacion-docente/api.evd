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

## Verificar que las migraciones están sanas

Corre esto antes de commitear una migración (y cuando cambies de rama):

1. `alembic heads` — debe imprimir **una sola** revisión marcada `(head)`. Si aparecen dos,
   dos ramas crearon migraciones en paralelo y hay que unirlas con `alembic merge`.
2. `alembic current` — la revisión de la BD. Debe resolver e idealmente coincidir con el head.
   Si dice `Can't locate revision identified by 'xxxx'`, la BD quedó sellada con una migración
   que ya no existe en `alembic/versions/` (típico al aplicar una migración de otra rama, o al
   borrar el archivo después de aplicarlo). Se repara con `alembic stamp --purge <revision_real>`.
3. `alembic check` — **el más importante**: compara los modelos con el esquema real de la BD.
   - `No new upgrade operations detected.` → modelos y BD están sincronizados.
   - Si lista operaciones, hay drift: falta una migración, o la BD tiene cambios que ninguna
     migración declara.
4. `alembic history` — la cadena debe ser lineal: cada `down_revision` apunta a la revisión anterior.

### Round-trip (probar que el downgrade funciona)

```
alembic downgrade -1
alembic upgrade head
alembic check
```

Si el `downgrade` explota, la migración no es reversible y hay que arreglar su `downgrade()`.

### Ojo con `create_all`

`api/app.py` llama a `Base.metadata.create_all()` al arrancar: eso **crea tablas nuevas** por su
cuenta, pero **nunca agrega columnas** a tablas existentes. Consecuencia: si levantas la app antes
de migrar, la tabla nueva ya existe y `alembic upgrade` falla con `DuplicateTable`. Por eso las
migraciones que crean tablas usan guardas de existencia (ver `b7c1d2e3f4a5`).

## Links / Docs
- Alembic docs: https://alembic.sqlalchemy.org/en/latest/
- FastAPI — SQL (Databases) tutorial: https://fastapi.tiangolo.com/tutorial/sql-databases/
- SQLAlchemy migrations (overview): https://docs.sqlalchemy.org/en/latest/core/metadata.html
