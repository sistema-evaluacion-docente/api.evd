# Checklist de configuración inicial (FastAPI + PostgreSQL)

Usa esto al arrancar un proyecto nuevo, antes de generar módulos.

## 1. Elegir sync vs async desde el inicio

No mezcles ambos estilos en el mismo proyecto.

- **Sync** (más simple, suficiente para la mayoría de apps CRUD):
  `SQLAlchemy` + `psycopg2` (o `psycopg3`) + `Session`.
- **Async** (mejor si hay alta concurrencia / muchas llamadas I/O paralelas):
  `SQLAlchemy 2.0` async + `asyncpg` + `AsyncSession`, endpoints `async def`,
  repositorios con `await self.db.execute(...)`.

Si el usuario no especifica, pregunta o usa sync por defecto — es más simple de
razonar y suficiente salvo que digan explícitamente que esperan alta concurrencia.

## 2. SQLAlchemy 2.0 — sintaxis nueva

Preferir `Mapped` y `mapped_column` sobre la sintaxis clásica `Column`:

```python
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4

class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
```

(Los ejemplos de `references/layer_examples.md` usan la sintaxis clásica por
compatibilidad amplia; ambas son válidas, usa la que el proyecto ya tenga.)

## 3. Alembic desde el día uno

No lo dejes para después — configúralo en el primer commit:

```bash
alembic init alembic
```

En `alembic/env.py`, importar `Base` de `app.core.database` y todos los modelos
para que el autogenerate los detecte:

```python
from app.core.database import Base
from app.models import user, order  # importar todos los modelos
target_metadata = Base.metadata
```

Cada cambio en `models/` requiere:
```bash
alembic revision --autogenerate -m "descripción del cambio"
alembic upgrade head
```

## 4. UUID vs ID secuencial

Usar `UUID` como PK si:
- La API expone IDs públicamente (evita IDs adivinables/enumerables).
- Se planea escalar horizontalmente o hacer sharding en el futuro.

Usar `Integer` autoincremental si:
- Es un proyecto interno/pequeño y la simplicidad/performance de índice importa más.

## 5. Variables de entorno con Pydantic Settings

```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

## 6. Evitar N+1 queries

Cualquier relación que se vaya a recorrer en un loop (ej. `order.items` para
cada order de una lista) debe cargarse explícitamente con `joinedload` o
`selectinload` en el repository — nunca dejarlo en lazy loading por defecto
si se sabe que se va a iterar.

## 7. Estructura de tests sugerida

```
tests/
├── unit/            # Testea services con repositories mockeados
└── integration/     # Testea repositories contra una DB de test real (o testcontainers)
```

Gracias a la inyección de dependencias, los services se testean sin DB real:
mockea el repository y verifica que la lógica de negocio se comporte correctamente.
