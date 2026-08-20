# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

API REST (FastAPI + PostgreSQL) del Sistema de Evaluación Docente de la UFPS. Sube PDFs de evaluación docente, los parsea, analiza comentarios estudiantiles con modelos de HuggingFace y expone reportes estadísticos y planes de mejora. Los mensajes de error y descripciones de auditoría de cara al usuario están **en español**; el código y los docstrings en inglés.

## Comandos

```bash
# Desarrollo (Docker) — hot reload, monta el repo en /app
make dev            # docker compose -f docker-compose.dev.yaml up
make prod           # docker compose -f docker-compose.yaml up

# Desarrollo local
source venv/bin/activate
fastapi dev api/app.py

# Tests (el venv del repo es ./venv)
./venv/bin/python -m pytest                                     # todo
./venv/bin/python -m pytest tests/unit/services/test_user_service.py
./venv/bin/python -m pytest tests/unit/services/test_user_service.py::TestUserService::test_create -q
./venv/bin/python -m pytest --cov=api --cov-report=html

# Migraciones
alembic revision --autogenerate -m "..."
alembic upgrade head
alembic check       # detecta drift entre modelos y BD — correr antes de commitear
```

Verificación rápida de que la app importa (los modelos se registran vía `api/app.py`):
`./venv/bin/python -c "import api.app"`.

Ver `MIGRATIONS.md` para el flujo completo, incluido el conflicto entre `Base.metadata.create_all()` (que `api/app.py` ejecuta al arrancar) y las migraciones que crean tablas: por eso esas migraciones llevan guardas de existencia.

No hay linter ni formateador configurado en CI; `pyproject.toml` solo configura pytest, coverage y unas reglas de pylint.

## Arquitectura

Flujo de una petición, en capas estrictas:

```
routes/ → controllers/ → services/ → repositories/ → models/
             ↑ dependencies/ (FastAPI Depends conecta las capas)
             ↓ serializers/ (model → dict)  schemas/ (Pydantic in/out)
```

- **routes/**: solo declaran el endpoint, aplican `require_roles(...)` y traducen `None` → `HTTPException(404)`.
- **controllers/**: delegación fina al service; construidos por una función `get_x_controller` al final del archivo.
- **services/**: toda la lógica de negocio, validaciones (lanzan excepciones de `api/exceptions`), commits y llamadas a `AuditService.log(...)` para mutaciones.
- **repositories/**: heredan de `BaseRepository[Model]` (`api/repositories/base.py`), que aporta `get/list/create/delete/paginate`. Cada repo expone `get_x_repository(db=Depends(get_db))`.
- **serializers/**: funciones `x_to_dict(model)` puras; los services devuelven **dicts**, no modelos ORM.

Excepción a la regla: `comparison` no tiene service — el controller habla directo con los repositorios. Al tocarlo, sigue el estilo del archivo en vez de introducir una capa nueva.

### Planes de mejoramiento

`improvement_plans` modela los **tres formatos oficiales de la UFPS** (ver `formatos-planes-mejoramiento.pdf`): Formato 1 (caso reportado por un programa académico → `improvement_plan_case_reports`), Formato 2 (ficha de acuerdo/acta) y Formato 3 (matriz de seguimiento). Los formatos se organizan en **cinco aspectos**: los 4 de `DIMENSION_MAP` más "Observaciones de los Estudiantes", que se justifica citando filas de `comments` (`improvement_plan_item_comments`). El catálogo `ASPECTS` en `api/utils/dimensions.py` es la fuente única de esa correspondencia.

El **acta tiene su propio ciclo de vida** (`acta_status`: `BORRADOR → CERRADA → FIRMADA`), independiente del estado del plan: al cerrarla se congela solo su contenido (items, asignaturas, número y fecha del acta, observaciones del Consejo) para poder imprimirla y firmarla; el resto del plan sigue editable. Solo un ADMIN puede reabrirla.

La **gestión de evidencias** es un ciclo entre director y docente: el director solicita un entregable concreto (`improvement_plan_evidence_requests`), el docente sube el archivo, ambos comentan en el hilo de la solicitud (`improvement_plan_evidence_comments`) y el director aprueba o rechaza. Una entrega pasa la solicitud a `EN_REVISION`; un rechazo la devuelve a `PENDIENTE` y deja un comentario de sistema para que el docente reenvíe. Cada transición notifica a la otra parte con `NotificationService` usando `link` para enlazar al plan.

Los tres formatos se **generan en PDF** con WeasyPrint + Jinja2: plantillas en `api/templates/improvement_plans/` (el Formato 3 va en horizontal), renderer puro en `api/utils/improvement_plan_pdf.py`, y el armado del contexto (agrupar items por aspecto, cruzar las notas de seguimiento) en `api/services/improvement_plan_document_service.py`. Flujo: `POST /{id}/documents/{formato}/generate` → descargar → firmar a mano → `POST .../signed`; subir el Formato 2 firmado pasa el acta a `FIRMADA`. WeasyPrint necesita librerías de sistema (Pango/HarfBuzz) — ya están en ambos Dockerfiles.

### Response envelope

Toda respuesta JSON exitosa se envuelve en `{status, data, pagination, error, timestamp}`. Hay **dos mecanismos que conviven** (ver `docs/adr/002-envelope-router.md`):

1. `EnvelopeRouter` (`api/core/router.py`) — los routers se declaran con `EnvelopeRouter(prefix=..., tags=[...])`, no con `APIRouter`. Envuelve el `response_model` en `ResponseEnvelope[T]` para que OpenAPI sea correcto, y desactiva la validación de respuesta en runtime.
2. `ResponseEnvelopeMiddleware` (`api/core/middleware.py`) — envuelve el body real. Si el dict de respuesta contiene las cuatro claves `total/page/limit/pages`, las extrae al campo `pagination` y promueve `items` a `data`.

Consecuencia práctica: un endpoint paginado devuelve `build_paginated_response(items, total, pagination)` (`api/schemas/pagination.py`) y declara `response_model=list[XOut]`. El middleware hace el resto. Rutas bajo `/docs`, `/redoc`, `/openapi.json`, `/uploads` y las `StreamingResponse` quedan fuera.

### Paginación

`PaginationDep` (`api/core/pagination.py`) inyecta `page`/`limit` (máx. 100) en la ruta; el repo llama `self.paginate(query, pagination)`; el service llama `build_paginated_response`.

### Errores

Todas las excepciones de dominio derivan de `AppException` (`api/exceptions/__init__.py`) con `code`, `message` en español y `status_code`. Los handlers globales (`api/exceptions/handlers.py`) las convierten al envelope de error. Para un recurso ausente, el service devuelve `None` y la ruta lanza el 404.

### Auth y roles

Firebase Admin SDK (`api/middlewares/auth.py`). `require_roles([RoleName.ADMIN, ...])` es una dependency factory que verifica el token, carga el usuario de la BD y **devuelve el dict del usuario** — por eso las rutas hacen `current_user=Depends(require_roles(_ROLES))` y lo pasan al controller para la auditoría. Roles: `ADMIN`, `DIRECTOR DE DEPARTAMENTO`, `DOCENTE`.

`UPLOAD_DIR` **no** se monta como estático: los PDFs y evidencias se sirven solo por endpoints con verificación de permisos (`GET /evaluations/{id}/pdf`).

### Procesamiento de evaluaciones

`POST /evaluations/upload` guarda el/los PDF en `uploads/evaluations/{periodo}/{department_id}/` y lanza un `BackgroundTasks`: `api/utils/pdf_parser.py` extrae docente/curso/22 preguntas en 4 dimensiones/comentarios → `api/utils/evaluation_processor.py` persiste → `api/utils/ai_analyzer.py` clasifica cada comentario por nivel de riesgo y categoría pedagógica (modelos HuggingFace configurados por `HUGGINGFACE_RISK_MODEL` / `HUGGINGFACE_CATEGORY_MODEL`). El progreso se emite por WebSocket.

La universidad publica **un reporte por tipo de programa**: presenciales y a distancia. El campo `file` del upload acepta uno o los dos PDFs; deben coincidir en periodo y departamento y ser de modalidades distintas, y quedan bajo una sola evaluación con sus rutas separadas por coma en `evaluations.pdf_url` (helpers en `api/utils/evaluation_pdfs.py`; los archivos se guardan con la modalidad en el nombre para poder distinguirlos después). La modalidad se lee del título que repite cada página (`Programas Presenciales` / `Programas a Distancia`), viaja en cada grupo del dict parseado y se persiste en `academic_groups.modality`; el catálogo está en `api/utils/modalities.py`. Un PDF cuyo título no declare la modalidad se rechaza.

### WebSockets

`api/core/websockets/` define `connection_manager.py` y los eventos tipados en `events.py`. Endpoints: `/ws/evaluations/{id}` (progreso), `/ws/notifications`, `/ws/devlogs` (solo con `DEBUG=true`; `BaseRepository._emit_db_event` publica los INSERT/DELETE). ADRs 004–006.

## Tests

Solo hay `tests/unit/` (repositories, services, controllers, más middleware y exceptions) — todo con `MagicMock`; no existe `tests/integration/` pese a lo que dice el README. `asyncio_mode = "auto"`, así que los tests `async def` no necesitan marker. Fixtures compartidos en `tests/conftest.py` (`mock_db`, `mock_user_model`, ...). Al añadir una feature, la convención es tocar las tres capas y sus tres archivos de test.

## Otros

- Configuración: `api/config.py` lee `.env` y expone el singleton `config`. `.env.example` lista las variables.
- Esquema de BD: `db.json` es un export de chartdb; actualízalo si cambia el esquema.
- ADRs en `docs/adr/`.
