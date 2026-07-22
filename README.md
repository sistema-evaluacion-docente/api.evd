# Sistema de Evaluación Docente

**API REST**
_Sistema de Evaluación Docente — Universidad Francisco de Paula Santander (UFPS)_

---

## ¿Qué es este proyecto?

Este repositorio contiene la API REST del **Sistema de Evaluación Docente**, desarrollado como parte de nuestro proyecto de grado en la Universidad Francisco de Paula Santander. El sistema automatiza el ciclo de evaluación docente: carga de PDF generados por el sistema universitario, extracción y procesamiento de datos, análisis de comentarios estudiantiles mediante un componente de inteligencia artificial, generación de reportes estadísticos y gestión de planes de seguimiento y mejora para docentes.

---

## Autores

| Autor              | Correo                                                                |
| ------------------ | --------------------------------------------------------------------- |
| Andrés Parra       | [andresalfonsopg@ufps.edu.co](mailto:andresalfonsopg@ufps.edu.co)                       |
| Orlando Beltrán    | [orlandojosebv@ufps.edu.co](mailto:orlandojosebv@ufps.edu.co)       |
| Alessandro Daniele | [alessandroumbertds@ufps.edu.co](mailto:alessandroumbertds@ufps.edu.co) |

---

## Descripción

API REST construida con **FastAPI** que automatiza el ciclo de evaluación docente en la Universidad Francisco de Paula Santander (UFPS). El sistema permite la carga de PDF generados por el sistema universitario, extrae y procesa los datos estructurados, analiza comentarios estudiantiles mediante modelos de inteligencia artificial (HuggingFace transformers), genera reportes estadísticos y gestiona planes de seguimiento y mejora para docentes.

---

## Funcionalidades principales

| Funcionalidad                    | Descripción                                                                                                                                                                         |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Carga y procesamiento de PDF** | Los directores de departamento suben formularios PDF de evaluación; el sistema extrae datos estructurados (docente, curso, puntajes, comentarios) mediante `pdfplumber` y `pikepdf` |
| **Análisis con IA**              | Los comentarios estudiantiles se clasifican automáticamente por nivel de riesgo y categoría pedagógica usando modelos de HuggingFace transformers                                   |
| **Reportes estadísticos**        | Promedios por departamento, historial por docente, distribuciones de calificaciones, rankings, análisis por dimensión/pregunta, exportación a Excel                                 |
| **Planes de seguimiento**        | Gestión de planes de mejora para docentes con items, evidencias, actas de compromiso y cierre                                                                          |
| **Comparación semestral**        | Comparación de métricas docentes entre dos períodos académicos                                                                                                                      |
| **Autenticación y roles**        | Firebase Auth con tres roles: ADMIN, DIRECTOR DE DEPARTAMENTO, DOCENTE                                                                                                              |
| **WebSockets en tiempo real**    | Progreso del procesamiento de evaluaciones y logs de desarrollo en vivo                                                                                                             |
| **Exportación a Excel**          | Reportes de evaluaciones y evaluaciones docentes en formato Excel                                                                                                                   |

---

## Arquitectura

El proyecto sigue una **arquitectura por capas** con separación clara de responsabilidades:

```
routes/        → Definición de endpoints HTTP y WebSocket
controllers/   → Orquestación y coordinación
services/      → Lógica de negocio
repositories/  → Acceso a datos (SQLAlchemy)
models/        → Modelos ORM
schemas/       → Esquemas Pydantic de request/response
serializers/   → Conversión modelo → dict
dependencies/  → Inyección de dependencias (FastAPI Depends)
```

```
api/
├── app.py                  # Creación de la aplicación FastAPI
├── config.py               # Configuración desde variables de entorno
├── database.py             # Engine SQLAlchemy, SessionLocal, get_db
├── core/                   # Middleware, paginación, router personalizado, WebSockets
├── exceptions/             # Excepciones de dominio y handlers globales
├── middlewares/            # Auth (Firebase) y dev logs
├── models/                 # 22 modelos ORM (SQLAlchemy)
├── schemas/                # Esquemas Pydantic
├── repositories/           # Capa de acceso a datos (CRUD genérico)
├── services/               # Lógica de negocio
├── controllers/            # Orquestación
├── routes/                 # Endpoints HTTP y WebSocket
├── dependencies/           # Inyección de dependencias
├── serializers/            # Conversión modelo → dict
└── utils/                  # Utilidades (parser PDF, IA, exportación Excel)
```

### Enlaces directos

| Recurso                     | Ruta                                   |
| --------------------------- | -------------------------------------- |
| Aplicación principal        | [api/app.py](api/app.py)               |
| Modelos ORM                 | [api/models/](api/models/)             |
| Rutas HTTP                  | [api/routes/](api/routes/)             |
| Servicios                   | [api/services/](api/services/)         |
| Repositorios                | [api/repositories/](api/repositories/) |
| Controladores               | [api/controllers/](api/controllers/)   |
| Esquemas Pydantic           | [api/schemas/](api/schemas/)           |
| Utilidades (PDF, IA, Excel) | [api/utils/](api/utils/)               |
| Migraciones                 | [alembic/](alembic/)                   |
| Tests                       | [tests/](tests/)                       |
| Migraciones (guía)          | [MIGRATIONS.md](MIGRATIONS.md)         |
| Decisiones de arquitectura  | [docs/adr/](docs/adr/)                 |

---

## Stack tecnológico

| Componente          | Tecnología                         |
| ------------------- | ---------------------------------- |
| Framework web       | FastAPI                            |
| ORM                 | SQLAlchemy                         |
| Base de datos       | PostgreSQL 16                      |
| Migraciones         | Alembic                            |
| Autenticación       | Firebase Admin SDK                 |
| Procesamiento PDF   | pdfplumber, pikepdf                |
| IA (NLP)            | HuggingFace transformers + PyTorch |
| NLP (anonymización) | spaCy                              |
| Exportación Excel   | openpyxl                           |
| Contenedores        | Docker + Docker Compose            |
| Tests               | pytest + coverage                  |

---

## Estructura del proyecto

```
api.evd/
├── api/
│   ├── app.py                  # Creación de la aplicación FastAPI
│   ├── config.py               # Configuración desde variables de entorno
│   ├── database.py             # Engine SQLAlchemy, SessionLocal, get_db
│   ├── core/                   # Middleware, paginación, router personalizado, WebSockets
│   ├── exceptions/             # Excepciones de dominio y handlers globales
│   ├── middlewares/            # Auth (Firebase) y dev logs
│   ├── models/                 # 22 modelos ORM (SQLAlchemy)
│   ├── schemas/                # Esquemas Pydantic de request/response
│   ├── repositories/           # Capa de acceso a datos (CRUD genérico)
│   ├── services/               # Lógica de negocio
│   ├── controllers/            # Orquestación
│   ├── routes/                 # Endpoints HTTP y WebSocket
│   ├── dependencies/           # Inyección de dependencias
│   ├── serializers/            # Conversión modelo → dict
│   └── utils/                  # Utilidades (parser PDF, IA, exportación Excel)
├── scripts/                    # Scripts de seed (roles, admin, settings)
├── tests/                      # Tests unitarios y de integración
├── alembic/                    # Migraciones de base de datos
├── docker/                     # Dockerfiles y entrypoints
└── uploads/                    # PDFs de evaluación cargados
```

### Enlaces directos

| Recurso                     | Ruta                                   |
| --------------------------- | -------------------------------------- |
| Aplicación principal        | [api/app.py](api/app.py)               |
| Modelos ORM                 | [api/models/](api/models/)             |
| Rutas HTTP                  | [api/routes/](api/routes/)             |
| Servicios                   | [api/services/](api/services/)         |
| Repositorios                | [api/repositories/](api/repositories/) |
| Controladores               | [api/controllers/](api/controllers/)   |
| Esquemas Pydantic           | [api/schemas/](api/schemas/)           |
| Utilidades (PDF, IA, Excel) | [api/utils/](api/utils/)               |
| Migraciones                 | [alembic/](alembic/)                   |
| Tests                       | [tests/](tests/)                       |
| Migraciones (guía)          | [MIGRATIONS.md](MIGRATIONS.md)         |
| Decisiones de arquitectura  | [docs/adr/](docs/adr/)                 |

---

## Flujo de procesamiento de evaluaciones

Esta sección describe **cómo se procesa una evaluación docente** desde que se sube el PDF hasta que los resultados están disponibles.

### Paso 1 — Carga del PDF

El director de departamento sube un formulario PDF de evaluación a través del endpoint `POST /evaluations/upload`. El archivo se valida (tamaño, tipo MIME) y se almacena en `uploads/evaluations/{periodo}/{department_id}/`.

### Paso 2 — Extracción de datos

El parser (`api/utils/pdf_parser.py`) procesa el PDF con `pdfplumber` y `pikepdf` para extraer:

- **Información del docente**: nombre, código institucional, dependencia
- **Información del curso**: nombre, código, grupo, período académico
- **Puntajes**: calificaciones para cada una de las 22 preguntas agrupadas en 4 dimensiones
- **Comentarios**: comentarios textuales de los estudiantes

### Paso 3 — Procesamiento en segundo plano

El endpoint `POST /evaluations/upload` inicia un `BackgroundTasks` que:

1. Crea o actualiza el usuario, docente y curso en la base de datos
2. Crea el grupo académico (curso + docente + período)
3. Almacena los puntajes de evaluación y puntajes por pregunta
4. Almacena los comentarios de estudiantes
5. Transmite el progreso en tiempo real vía WebSocket (`/ws/evaluations/{id}`)

### Paso 4 — Análisis con IA

Los comentarios estudiantiles se procesan con pipelines de HuggingFace transformers (`api/utils/ai_analyzer.py`):

- **Clasificación de riesgo**: determina si un comentario es positivo, neutro o negativo
- **Clasificación pedagógica**: asigna categorías pedagógicas a cada comentario

### Paso 5 — Reportes y visualización

El sistema expone endpoints para consultar:

- Promedios por departamento y período académico
- Historial completo por docente
- Distribuciones de calificaciones
- Rankings docentes
- Puntajes por dimensión y por pregunta
- Comparación entre dos semestres
- Exportación a Excel de evaluaciones y evaluaciones docentes

---

## Requisitos

- Python 3.12+
- PostgreSQL 16
- Firebase project (para autenticación)

Las dependencias se encuentran en `requirements.txt`:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

---

## Uso

### Desarrollo

```bash
# Con Docker
docker compose -f docker-compose.dev.yaml up

# Sin Docker
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
fastapi dev api/app.py
```

### Producción

```bash
docker compose -f docker-compose.yaml up
```

### Migraciones

```bash
alembic upgrade head
```

Ver [MIGRATIONS.md](MIGRATIONS.md) para el flujo de trabajo completo.

### Seed (roles + admin)

```bash
# 1. Ejecutar migraciones
alembic upgrade head

# 2. Configurar variables de entorno requeridas
export SEED_ADMIN_UID=<firebase_uid>
export SEED_ADMIN_EMAIL=<email>

# 3. (Opcional)
export SEED_ADMIN_USERNAME=<username>
export SEED_ADMIN_NAME=<name>
export SEED_ADMIN_AVATAR_URL=<url>
export SEED_ADMIN_DEPARTMENT_ID=<id>
export SEED_ADMIN_ROLES=ADMIN

# 4. Ejecutar seed
python scripts/seed_roles_admin.py
```

---

## Endpoints principales

| Prefijo                       | Tags                       | Operaciones principales                                                                                                                            |
| ----------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/health`                     | Health                     | `GET /`                                                                                                                                            |
| `/users`                      | Users                      | CRUD, login/auth, gestión de roles                                                                                                                 |
| `/teachers`                   | Teachers                   | CRUD, carga masiva (Excel/CSV), historial, promedios                                                                                               |
| `/courses`                    | Courses                    | CRUD                                                                                                                                               |
| `/departments`                | Departments                | CRUD, asignar/desasignar director                                                                                                                  |
| `/directors`                  | Directors                  | CRUD                                                                                                                                               |
| `/faculties`                  | Faculties                  | CRUD                                                                                                                                               |
| `/academic-groups`            | Academic Groups            | CRUD                                                                                                                                               |
| `/academic-periods`           | Academic Periods           | CRUD, activar/cerrar                                                                                                                               |
| `/evaluations`                | Evaluations                | Subir PDF, listar, resumen por período, promedios por dimensión, comentarios por docente, detalle por docente, exportar Excel, análisis IA, estado |
| `/evaluation-scores`          | Evaluation Scores          | Listar, obtener por ID, por evaluación                                                                                                             |
| `/evaluation-question-scores` | Evaluation Question Scores | Obtener por ID, por evaluation score                                                                                                               |
| `/comments`                   | Comments                   | Listar, contar por departamento/período, contar por docente                                                                                        |
| `/audits`                     | Audits                     | Listar (paginado), obtener por ID                                                                                                                  |
| `/stats`                      | Stats                      | Promedios por departamento, historial por docente, rankings, distribución de notas, análisis por materia, comparativa docente vs departamento      |
| `/comparison`                 | Comparison                 | Comparar docente entre dos semestres                                                                                                               |
| `/settings`                   | Settings                   | CRUD + historial                                                                                                                                   |
| `/improvement-plans`          | Improvement Plans          | CRUD, filtros, docentes en riesgo, candidatos, indicadores, acta, evidencias, evaluar, cerrar                                                      |
| `/admin/dashboard`            | Admin Dashboard            | Dashboard con datos agregados                                                                                                                      |
| `/ws/devlogs`                 | (WebSocket)                | Logs de desarrollo en tiempo real                                                                                                                  |
| `/ws/evaluations/{id}`        | (WebSocket)                | Progreso del procesamiento de evaluaciones                                                                                                         |

---

## Tests

```
tests/
├── conftest.py                 # Fixtures compartidos
├── unit/                       # Tests unitarios (mocks)
│   ├── repositories/           # Tests de la capa de repositorios
│   ├── services/               # Tests de la capa de servicios
│   ├── controllers/            # Tests de la capa de controladores
│   ├── test_middleware.py      # Tests del middleware de envelope
│   └── test_exceptions.py     # Tests de los exception handlers
└── integration/                # Tests de integración (requieren DB)
    └── test_users_routes.py    # Tests de rutas HTTP
```

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

> **Nota:** Los tests de integración con autenticación están skippeados porque requieren una base de datos real. Para tests de integración completos, se recomienda usar `pytest-postgresql` o `testcontainers`. Los tests unitarios mockean todas las dependencias externas.

---

## Base de datos

Visita [https://chartdb.byandrev.dev](https://chartdb.byandrev.dev) e importa el archivo `db.json` para visualizar el esquema de la base de datos. Si realizas cambios, exporta el JSON y actualiza el archivo en el repositorio.

---

## Referencias

- [FastAPI](https://fastapi.tiangolo.com/) — Framework web
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM
- [PostgreSQL](https://www.postgresql.org/) — Base de datos
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup) — Autenticación
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/index) — Modelos de NLP
- [pdfplumber](https://github.com/jsvine/pdfplumber) — Extracción de PDF
- [pikepdf](https://github.com/pikepdf/pikepdf) — Procesamiento de PDF

---

## Licencia

El código se distribuye bajo la licencia MIT, disponible en [LICENSE](LICENSE).
