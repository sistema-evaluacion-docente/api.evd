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
```

## Ejecutar tests

```bash
# Ejecutar todos los tests
pytest

# Ejecutar con verbose
pytest -v

# Ejecutar solo tests unitarios
pytest tests/unit/

# Ejecutar un archivo específico
pytest tests/unit/services/test_user_service.py

# Ejecutar con coverage
pytest --cov=api --cov-report=html
```

## Cobertura

Los tests cubren las siguientes capas:

- **Repository**: Tests de queries y operaciones CRUD con DB mockeada
- **Service**: Tests de lógica de negocio con repositorios mockeados
- **Controller**: Tests de delegación a servicios
- **Middleware**: Tests del envelope de respuesta
- **Exceptions**: Tests de los handlers de excepciones
- **Routes**: Tests de integración HTTP (algunos skippeados por requerir DB real)

## Fixtures

Los fixtures compartidos están en `conftest.py`:

- `mock_db`: Sesión de DB mockeada
- `mock_user_model`: Instancia de UserModel mockeada
- `mock_role_model`: Instancia de RoleModel mockeada
- `sample_user_data`: Datos de usuario de ejemplo
- `sample_user_create`: Schema UserCreate de ejemplo

## Notas

- Los tests de integración con autenticación están skippeados porque requieren una DB real
- Para tests de integración completos, se recomienda usar pytest-postgresql o testcontainers
- Los tests unitarios mockean todas las dependencias externas
