# Ejemplos de código por capa

Referencia completa para generar cada capa consistentemente. Usa estos snippets
como plantilla, adaptando nombres de entidades/campos al dominio del usuario.

## models/ — SQLAlchemy (solo tablas, sin lógica)

```python
# models/user.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
```

```python
# models/order.py
from sqlalchemy import Column, ForeignKey, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="orders")
    items = relationship("OrderItem", back_populates="order")
```

## schemas/ — Pydantic (serializers)

Separa siempre input de output. No reutilices el mismo schema para crear y responder.

```python
# schemas/user.py
from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: EmailStr | None = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    model_config = ConfigDict(from_attributes=True)
```

```python
# schemas/analytics.py — DTO para resultados que no mapean a un modelo
from pydantic import BaseModel
from uuid import UUID

class TopProduct(BaseModel):
    id: UUID
    name: str
    total_sold: int
```

## repositories/ — CRUD genérico + queries específicas

```python
# repositories/base.py
from typing import Generic, TypeVar
from uuid import UUID
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: UUID) -> ModelType | None:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def list(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj_in: dict) -> ModelType:
        obj = self.model(**obj_in)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: UUID) -> None:
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
```

```python
# repositories/user_repository.py
from app.repositories.base import BaseRepository
from app.models.user import User
from sqlalchemy.orm import Session

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()
```

### Queries complejas: joins, agregaciones, SQL crudo

```python
# repositories/order_repository.py
from sqlalchemy.orm import joinedload
from app.repositories.base import BaseRepository
from app.models.order import Order

class OrderRepository(BaseRepository[Order]):
    def __init__(self, db):
        super().__init__(Order, db)

    def get_orders_with_user_and_items(self, user_id):
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.user),
                joinedload(Order.items).joinedload("product"),
            )
            .filter(Order.user_id == user_id)
            .all()
        )
```

```python
# repositories/analytics_repository.py
# Reportes/agregaciones pesadas van separados del CRUD simple
from sqlalchemy import func, extract, desc, text
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product

class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_top_selling_products(self, limit: int = 10):
        return (
            self.db.query(
                Product.id,
                Product.name,
                func.sum(OrderItem.quantity).label("total_sold"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id, Product.name)
            .order_by(desc("total_sold"))
            .limit(limit)
            .all()
        )

    def get_monthly_revenue(self, year: int):
        return (
            self.db.query(
                extract("month", Order.created_at).label("month"),
                func.sum(Order.total).label("revenue"),
            )
            .filter(extract("year", Order.created_at) == year)
            .group_by("month")
            .order_by("month")
            .all()
        )

    def get_custom_report(self):
        # SQL crudo cuando el ORM no expresa bien la query — siempre en repository
        result = self.db.execute(text("SELECT ... FROM ... WHERE ..."))
        return result.fetchall()
```

## services/ — lógica de negocio (nunca SQL/ORM directo)

```python
# services/user_service.py
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.exceptions.handlers import UserAlreadyExistsError

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register_user(self, data: UserCreate):
        if self.repo.get_by_email(data.email):
            raise UserAlreadyExistsError()
        hashed = hash_password(data.password)
        payload = {**data.model_dump(exclude={"password"}), "hashed_password": hashed}
        return self.repo.create(payload)
```

```python
# services/analytics_service.py
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import TopProduct

class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository):
        self.repo = repo

    def top_products(self, limit: int = 10) -> list[TopProduct]:
        rows = self.repo.get_top_selling_products(limit)
        return [TopProduct(id=r.id, name=r.name, total_sold=r.total_sold) for r in rows]
```

## api/v1/ — controllers (thin, sin lógica)

```python
# api/v1/users.py
from fastapi import APIRouter, Depends
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.dependencies.auth import get_user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, service: UserService = Depends(get_user_service)):
    return service.register_user(data)
```

## dependencies/ — wiring de Depends()

```python
# dependencies/auth.py (o providers.py)
from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)
```
