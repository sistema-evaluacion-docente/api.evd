# Ejemplos completos de tests por capa

## conftest.py — fixtures compartidas

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def mock_user_repository():
    """Repository mockeado, para tests de service."""
    return MagicMock()

@pytest.fixture
def client():
    """TestClient para tests de endpoints."""
    return TestClient(app)
```

## unit/services/ — mockeando el repository

```python
# tests/unit/services/test_user_service.py
import pytest
from app.services.user_service import UserService
from app.schemas.user import UserCreate
from app.exceptions.handlers import UserAlreadyExistsError

@pytest.fixture
def service(mock_user_repository):
    return UserService(mock_user_repository)

def test_register_user_with_new_email_creates_user(service, mock_user_repository):
    mock_user_repository.get_by_email.return_value = None
    mock_user_repository.create.return_value = MagicMockUser(email="new@test.com")

    data = UserCreate(email="new@test.com", password="secret123")
    result = service.register_user(data)

    mock_user_repository.get_by_email.assert_called_once_with("new@test.com")
    mock_user_repository.create.assert_called_once()
    assert result.email == "new@test.com"

def test_register_user_with_duplicate_email_raises_error(service, mock_user_repository):
    mock_user_repository.get_by_email.return_value = ExistingUser()

    data = UserCreate(email="existing@test.com", password="secret123")

    with pytest.raises(UserAlreadyExistsError):
        service.register_user(data)

    mock_user_repository.create.assert_not_called()

def test_register_user_hashes_password_before_saving(service, mock_user_repository):
    mock_user_repository.get_by_email.return_value = None
    mock_user_repository.create.return_value = MagicMockUser()

    data = UserCreate(email="new@test.com", password="plaintext")
    service.register_user(data)

    saved_payload = mock_user_repository.create.call_args[0][0]
    assert saved_payload["hashed_password"] != "plaintext"
    assert "password" not in saved_payload
```

Nota: `MagicMockUser` y `ExistingUser` arriba son helpers de fábrica para
construir objetos simulados con los atributos que el test necesita — defínelos
en el propio archivo de test o en un `factories.py` si se repiten mucho.

## integration/repositories/ — DB real de test con testcontainers

```python
# tests/conftest.py (agregar)
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

@pytest.fixture
def db_session(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
```

```python
# tests/integration/repositories/test_user_repository.py
import pytest
from app.repositories.user_repository import UserRepository

@pytest.fixture
def repo(db_session):
    return UserRepository(db_session)

def test_create_and_get_user(repo):
    user = repo.create({"email": "test@test.com", "hashed_password": "hash"})
    fetched = repo.get(user.id)
    assert fetched.email == "test@test.com"

def test_get_by_email_when_not_exists_returns_none(repo):
    assert repo.get_by_email("nope@test.com") is None

def test_create_with_duplicate_email_raises_integrity_error(repo):
    from sqlalchemy.exc import IntegrityError
    repo.create({"email": "dup@test.com", "hashed_password": "hash"})
    with pytest.raises(IntegrityError):
        repo.create({"email": "dup@test.com", "hashed_password": "hash2"})
```

### Testeando queries complejas (joins, agregaciones)

```python
# tests/integration/repositories/test_analytics_repository.py
def test_get_top_selling_products_orders_by_quantity_desc(db_session, seed_orders):
    repo = AnalyticsRepository(db_session)
    results = repo.get_top_selling_products(limit=3)

    assert len(results) <= 3
    assert results[0].total_sold >= results[-1].total_sold
```

`seed_orders` sería una fixture propia que inserta datos de prueba antes del
test — créala junto al test si no existe ya en `conftest.py`.

## unit/api/ — endpoint con Depends() override

```python
# tests/unit/api/test_users_endpoints.py
import pytest
from unittest.mock import MagicMock
from app.main import app
from app.dependencies.auth import get_user_service

@pytest.fixture
def mock_service():
    return MagicMock()

@pytest.fixture
def client_with_mock_service(client, mock_service):
    app.dependency_overrides[get_user_service] = lambda: mock_service
    yield client
    app.dependency_overrides.clear()

def test_create_user_with_valid_payload_returns_201(client_with_mock_service, mock_service):
    mock_service.register_user.return_value = FakeUser(id="123", email="new@test.com")

    response = client_with_mock_service.post(
        "/users/", json={"email": "new@test.com", "password": "secret123"}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new@test.com"

def test_create_user_with_invalid_email_returns_422(client_with_mock_service):
    response = client_with_mock_service.post(
        "/users/", json={"email": "not-an-email", "password": "secret123"}
    )
    assert response.status_code == 422

def test_create_user_with_duplicate_email_returns_409(client_with_mock_service, mock_service):
    from app.exceptions.handlers import UserAlreadyExistsError
    mock_service.register_user.side_effect = UserAlreadyExistsError()

    response = client_with_mock_service.post(
        "/users/", json={"email": "dup@test.com", "password": "secret123"}
    )
    assert response.status_code == 409
```

## Async: si el proyecto usa AsyncSession

```python
# tests/conftest.py (variante async)
import pytest_asyncio

@pytest_asyncio.fixture
async def async_client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

```python
# tests/unit/api/test_users_endpoints.py (variante async)
import pytest

@pytest.mark.asyncio
async def test_create_user_returns_201(async_client, mock_service_override):
    response = await async_client.post(
        "/users/", json={"email": "new@test.com", "password": "secret123"}
    )
    assert response.status_code == 201
```
