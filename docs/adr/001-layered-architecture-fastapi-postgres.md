# ADR-001: Arquitectura por capas con FastAPI y PostgreSQL

- **Estado**: Aceptado
- **Fecha**: 2026-07-18
- **Decisores**: Equipo de desarrollo

## Contexto

El proyecto **api.evd** es un sistema de evaluacion docente que requiere una API REST para gestionar docentes, evaluaciones, departamentos, facultades, planes de mejora y demas entidades academicas. Se necesitaba una arquitectura que permitiera:

- Separacion clara de responsabilidades.
- Facilidad para escribir tests unitarios e integration tests.
- Escalabilidad del codigo a medida que crecen los modulos del dominio.
- Mantenibilidad a largo plazo por multiples desarrolladores.

## Decision

Se adopto una **arquitectura por capas** (layered architecture) sobre **FastAPI** con **PostgreSQL** como base de datos relacional. Las capas y tecnologias elegidas son:

### Capas

```
HTTP Request
    |
    v
+-----------+
|  Routes   |  <-- Define endpoints, inyecta dependencias, aplica auth/roles
+-----------+
    |
    v
+--------------+
| Controllers  |  <-- Coordina la logica de presentacion, delega al service
+--------------+
    |
    v
+-----------+
|  Services  |  <-- Logica de negocio, orquesta repositorios y validaciones
+-----------+
    |
    v
+---------------+
| Repositories  |  <-- Acceso a datos (SQLAlchemy queries)
+---------------+
    |
    v
+--------+
| Models |  <-- Definicion de tablas (SQLAlchemy ORM)
+--------+
    |
    v
 PostgreSQL
```

### Estructura de directorios

```
api/
├── app.py                  # Punto de entrada FastAPI
├── config.py               # Configuracion via variables de entorno
├── database.py             # Engine, SessionLocal, Base, get_db
├── routes/                 # Capa HTTP: endpoints y routers
├── controllers/            # Capa de coordinacion por modulo
├── services/               # Capa de logica de negocio
├── repositories/           # Capa de acceso a datos
│   └── base.py             # BaseRepository generico (CRUD basico)
├── models/                 # Modelos SQLAlchemy (tablas)
├── schemas/                # Schemas Pydantic (request/response DTOs)
├── serializers/            # Funciones para convertir modelos a dicts
├── dependencies/           # Inyeccion de dependencias (FastAPI Depends)
├── middlewares/             # Middleware de autenticacion (Firebase)
├── core/                   # Middleware de envelope, paginacion
├── exceptions/             # Excepciones de dominio y handlers globales
└── utils/                  # Utilidades transversales (PDF parser, AI, etc.)
```

### Patrones clave

| Patron | Descripcion |
|--------|-------------|
| **Repository Pattern** | Cada entidad tiene su repositorio que hereda de `BaseRepository[T]` con operaciones CRUD genericas (`get`, `list`, `create`, `delete`, `paginate`). |
| **Dependency Injection** | FastAPI `Depends` para inyectar repositorios en services, services en controllers, y controllers en routes. Cada capa solo conoce la interfaz de la capa inferior. |
| **Response Envelope** | Middleware (`ResponseEnvelopeMiddleware`) que envuelve todas las respuestas JSON en un formato estandar: `{ status, data, pagination, error, timestamp }`. |
| **Domain Exceptions** | Jerarquia de excepciones propias (`AppException` como base) con handlers globales que mapean a respuestas HTTP con codigos de error semanticos. |
| **Schemas (Pydantic)** | DTOs separados para input (`UserCreate`, `UserUpdate`), output (`UserOut`), filtros (`UserFilters`) y paginacion (`Page[T]`). |
| **Serializers** | Funciones puras que convierten modelos SQLAlchemy a dicts para los schemas de salida, desacoplando el modelo de dominio de la representacion API. |
| **Generic Pagination** | `PaginationParams` + `Page[T]` reutilizables en todos los endpoints de lista. |

### Stack tecnologico

| Componente | Tecnologia |
|------------|-----------|
| Framework HTTP | FastAPI + Uvicorn |
| ORM | SQLAlchemy (declarative, mapped_column) |
| Migraciones | Alembic |
| Base de datos | PostgreSQL 16 |
| Autenticacion | Firebase Admin SDK |
| Validacion | Pydantic v2 |
| Contenerizacion | Docker + Docker Compose |
| Testing | pytest (unit + integration) |
| Procesamiento | pdfplumber, pikepdf, spacy, transformers |

## Consecuencias

### Positivas

- **Testabilidad**: Cada capa puede mockearse independientemente. Los repositories pueden mockearse en tests de services; los services en tests de controllers.
- **Separacion de responsabilidades**: Cada modulo tiene un unico proposito claro. Routes no contienen logica de negocio; repositories no contienen reglas de dominio.
- **Consistencia**: El patron se repite para cada modulo (users, teachers, evaluations, etc.), facilitando que nuevos desarrolladores entiendan el codigo rapidamente.
- **Flexibilidad**: Cambiar la base de datos o el ORM solo afecta la capa de repositories. Cambiar reglas de negocio solo afecta services.
- **Envelope uniforme**: El cliente siempre recibe el mismo formato de respuesta, simplificando el consumo de la API.

### Negativas

- **Boilerplate**: Cada nuevo modulo requiere crear archivos en 6+ capas (model, repository, service, controller, route, schema, serializer, dependencies).
- **Complejidad en consultas complejas**: Queries con multiples joins o reportes pueden requerir salir del patron de repository (se maneja con repositories especializados como `comparison` o `stats`).
- **Curva de aprendizaje**: Nuevos miembros deben entender la convencion de capas, la inyeccion de dependencias via `Depends`, y el sistema de excepciones de dominio.

### Riesgos mitigados

- El `BaseRepository` generico reduce el boilerplate para operaciones CRUD estandar.
- Los handlers globales de excepciones evitan duplicar logica de error en cada endpoint.
- La estructura de directorios espejo (mismo nombre de modulo en cada capa) facilita la navegacion.
