---
name: fastapi-postgres-architecture
description: Guía de arquitectura por capas para proyectos FastAPI con PostgreSQL (SQLAlchemy + Alembic). Usa esta skill siempre que el usuario esté creando, estructurando o refactorizando un backend en FastAPI, cuando mencione "estructura de carpetas", "repositories", "services", "controllers", "serializers/schemas", organización de un proyecto Python con FastAPI, o cuando pida ayuda para escribir queries complejas (joins, agregaciones, reportes) en un proyecto que ya sigue este patrón. Aplica también si el usuario menciona SQLAlchemy, Alembic, Pydantic schemas, o pide revisar/generar un CRUD, endpoint, o módulo nuevo dentro de un proyecto FastAPI existente.
---

# Arquitectura FastAPI + PostgreSQL (capas)

Skill para diseñar, generar y mantener proyectos FastAPI con PostgreSQL siguiendo
una arquitectura por capas (layered architecture): `api → services → repositories → models`.

## Cuándo usar esta skill

- El usuario está arrancando un proyecto FastAPI nuevo y pregunta cómo organizarlo.
- El usuario tiene un proyecto FastAPI ya estructurado así y pide agregar un módulo
  nuevo (ej. "agrega el CRUD de productos", "necesito un endpoint de reportes").
- El usuario pide una query compleja (joins, agregaciones, reportes) — debe ir en
  `repositories/`, nunca en `services/` ni en `api/`.
- El usuario pregunta dónde debería vivir cierta lógica (validación, transacción,
  serialización, acceso a datos).

Si el proyecto del usuario NO sigue esta arquitectura y no pide adoptarla, no la
impongas — pregunta primero si quiere migrar o solo necesita ayuda puntual.

## Regla de oro (dependencias entre capas)

```
api (controllers) → services → repositories → models
schemas (Pydantic) se usan en api y services, NUNCA en repositories
```

- Un controller (`api/`) nunca llama directo a un repository. Siempre pasa por un service.
- Un repository nunca conoce schemas ni lógica de negocio — solo queries.
- Un service nunca construye SQL/ORM directamente (`.filter()`, `.join()`, `text()`)
  — eso siempre va en el repository, aunque sea una query "simple".
- Los modelos SQLAlchemy (`models/`) son solo definición de tablas, sin lógica.

## Estructura de carpetas estándar

```
app/
├── main.py                    # Punto de entrada, crea la app FastAPI
├── core/
│   ├── config.py               # Settings con Pydantic BaseSettings (.env)
│   ├── security.py             # JWT, hashing de passwords
│   └── database.py             # Engine, SessionLocal, get_db()
│
├── models/                     # SQLAlchemy models (tablas), sin lógica
│   ├── user.py
│   └── order.py
│
├── schemas/                    # Pydantic — "serializers" de FastAPI
│   ├── user.py                 # UserCreate, UserUpdate, UserResponse
│   └── order.py
│
├── repositories/                # Acceso a datos: CRUD + queries complejas
│   ├── base.py                  # CRUD genérico reutilizable
│   ├── user_repository.py
│   ├── order_repository.py
│   └── analytics_repository.py  # Reportes/agregaciones pesadas, aparte del CRUD
│
├── services/                    # Lógica de negocio, validaciones, orquestación
│   ├── user_service.py
│   └── order_service.py
│
├── api/
│   └── v1/
│       ├── router.py             # Agrega todos los sub-routers
│       ├── users.py
│       └── orders.py
│
├── dependencies/                 # Depends() reutilizables (get_db, get_*_service)
│   └── auth.py
│
├── exceptions/                   # Excepciones custom + handlers
│   └── handlers.py
│
└── alembic/
    └── versions/

tests/
├── unit/
└── integration/

.env
alembic.ini
requirements.txt / pyproject.toml
```

Al crear un módulo nuevo (ej. "products"), genera SIEMPRE estos 4 archivos en paralelo,
en este orden: `models/product.py` → `schemas/product.py` → `repositories/product_repository.py`
→ `services/product_service.py` → `api/v1/products.py`. No saltes capas.

## Patrones por capa

Para el código de referencia de cada capa (modelo, schema, repository base y con
queries complejas, service, controller, wiring de dependencias) lee:

- `references/layer_examples.md` — snippets completos y comentados de cada capa,
  incluyendo joins, agregaciones (`func.sum`, `group_by`), SQL crudo con `text()`,
  y cómo devolver DTOs para resultados que no mapean a un modelo.
- `references/setup_checklist.md` — checklist de configuración inicial: SQLAlchemy 2.0,
  async vs sync, Alembic, UUID vs ID secuencial, variables de entorno.

## Reglas rápidas para queries complejas

1. **Nombra por intención, no por implementación**: `get_top_selling_products()`,
   no `join_products_orderitems()`.
2. **Si el resultado no mapea a un modelo** (agregaciones, columnas sueltas), créale
   un schema/DTO propio en `schemas/` (ej. `TopProduct`) y conviértelo en el repository
   antes de devolverlo.
3. **Reportes pesados van en un repository separado** (`analytics_repository.py`),
   no mezclados con el CRUD simple de la entidad.
4. **SQL crudo también va en el repository**, usando `text()` — nunca en service o controller.

## Checklist antes de dar por terminado un módulo nuevo

- [ ] `models/` no importa nada de `schemas/` ni `services/`
- [ ] `repositories/` no importa `schemas/` (recibe/devuelve dicts o modelos; el service
      convierte a schema si aplica)
- [ ] `services/` no contiene ningún `.query(`, `.filter(`, `.join(` ni `text(`
- [ ] `api/` solo recibe request → llama service → devuelve `response_model`
- [ ] Toda relación N-N o consulta con joins usa `joinedload`/`selectinload` explícito
      para evitar N+1 queries
- [ ] Hay migración de Alembic generada para cualquier cambio en `models/`
