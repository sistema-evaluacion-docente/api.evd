---
name: fastapi-unit-testing
description: Guía para escribir unit tests e integration tests en proyectos FastAPI + PostgreSQL que siguen arquitectura por capas (api/services/repositories/models). Usa esta skill siempre que el usuario pida "crear tests", "unit tests", "testear el service/repository/endpoint", "cobertura de tests", "mockear repositories", o cuando pida agregar tests para un CRUD o módulo nuevo. También aplica si menciona pytest, pytest-mock, fixtures, TestClient de FastAPI, o testcontainers. Complementa (no reemplaza) la skill fastapi-postgres-architecture — asume que el proyecto sigue esa estructura de capas.
---

# Unit Testing para FastAPI + PostgreSQL (arquitectura por capas)

Skill para generar tests consistentes en proyectos que separan
`api → services → repositories → models`. La regla central: **cada capa se
testea de forma aislada, mockeando la capa inmediatamente inferior.**

## Cuándo usar esta skill

- El usuario pide tests para un service, repository, o endpoint específico.
- El usuario pide "cobertura de tests" para un CRUD completo (ej. Users, Orders).
- El usuario refactorizó código usando `fastapi-postgres-architecture` y ahora
  quiere tests para lo refactorizado.
- El usuario pregunta cómo mockear la base de datos o un repository.

Si el proyecto no sigue la arquitectura por capas, adapta el enfoque pero
mantén el principio: nunca testear lógica de negocio contra una base de
datos real si se puede mockear la capa de datos.

## Principio central: qué se mockea en cada capa

```
Testing services      → mockea repositories (no toques la DB)
Testing repositories   → usa una DB de test real (Postgres en Docker/testcontainers)
Testing api/endpoints   → usa TestClient + override de Depends() con mocks o DB de test
```

No mockees SQLAlchemy internamente ni simules queries — o usas una DB de test
real (para repositories) o mockeas el repository completo (para services).
Mockear a mitad de camino (ej. mockear `db.query()`) genera tests frágiles
que no reflejan el comportamiento real.

## Stack recomendado

- `pytest` como test runner
- `pytest-mock` (fixture `mocker`) para mocks, o `unittest.mock` si el usuario
  prefiere stdlib
- `httpx.AsyncClient` o `fastapi.testclient.TestClient` para tests de endpoints
- `pytest-asyncio` si el proyecto es async
- Para repositories: una base de datos Postgres de test real, vía
  `testcontainers-python` (recomendado, aísla completamente) o una DB de test
  fija en `docker-compose.test.yml`. Nunca usar SQLite como sustituto de
  Postgres — hay diferencias de tipos (UUID, JSONB, arrays) que esconden bugs.

## Estructura de carpetas de tests

```
tests/
├── conftest.py                    # Fixtures compartidas (db_session, client, mocks)
├── unit/
│   ├── services/
│   │   ├── test_user_service.py
│   │   └── test_order_service.py
│   └── api/
│       ├── test_users_endpoints.py
│       └── test_orders_endpoints.py
└── integration/
    └── repositories/
        ├── test_user_repository.py
        └── test_order_repository.py
```

Un archivo de test por archivo de origen (`services/user_service.py` →
`tests/unit/services/test_user_service.py`). No mezcles tests de distintos
services/repositories en el mismo archivo.

## Qué testear en cada capa

### services/ (unit, repository mockeado)

- Cada regla de negocio explícita (ej. "no permitir email duplicado")
- Cada excepción custom que el service puede lanzar
- Que el service llame al método correcto del repository con los argumentos
  correctos (usando `assert_called_once_with`)
- Transformaciones de datos antes de pasar al repository (ej. hashing de password)

**No testear en services**: detalles de implementación de SQL/ORM — eso es
responsabilidad de los tests de repository.

### repositories/ (integration, DB real de test)

- Que el CRUD básico funcione contra Postgres real (create/get/update/delete)
- Constraints de la base de datos (unique, foreign key, not null)
- Queries complejas: que un join devuelva los datos esperados, que una
  agregación calcule el valor correcto
- Casos límite: registro no encontrado, lista vacía, filtros que no matchean nada

### api/ (endpoint, TestClient + Depends override)

- Status codes correctos (200, 201, 404, 422, etc.)
- Que el `response_model` serialice correctamente (campos esperados, tipos)
- Validación de input (422 cuando el payload no cumple el schema)
- Que errores del service se traduzcan al status code HTTP correcto
  (ej. `UserAlreadyExistsError` → 409)

**No testear en api/**: lógica de negocio — eso ya se cubrió en el test del
service. El test de endpoint solo verifica el "cableado" HTTP.

## Referencias

Para el código completo de fixtures y ejemplos de cada tipo de test, lee:

- `references/test_examples.md` — fixtures de conftest.py, mocks de
  repository con pytest-mock, tests de service/repository/endpoint completos,
  setup de testcontainers para Postgres.
- `references/checklist.md` — checklist de qué no debe faltar antes de dar
  por completa la cobertura de un módulo.

## Convención de nombres

```python
def test_<método>_<escenario>_<resultado_esperado>():
    ...

# Ejemplos:
def test_register_user_with_duplicate_email_raises_error(): ...
def test_get_by_email_when_user_exists_returns_user(): ...
def test_create_user_endpoint_with_valid_payload_returns_201(): ...
```

## Al generar tests para un módulo completo

1. Identifica las 3 capas existentes del módulo (service, repository, api).
2. Genera primero los tests de service (son los más rápidos de escribir y
   ejecutar, no requieren DB).
3. Genera tests de repository solo si el usuario tiene un entorno de DB de
   test configurado — si no, pregunta antes de asumir testcontainers.
4. Genera tests de endpoint al final, mockeando el service completo vía
   `app.dependency_overrides`.
5. Corre los tests (`pytest tests/ -v`) y reporta resultados; si algo falla
   por un bug real en el código (no en el test), avisa antes de "arreglar"
   el test para que pase.
