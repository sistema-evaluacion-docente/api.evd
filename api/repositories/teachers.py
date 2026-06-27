"""
Teachers repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.schemas.teacher import TeacherCreate, TeacherUpdate
from api.serializers.teachers import teacher_to_dict


class TeachersRepository:
    """Teachers repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: TeacherCreate) -> dict:
        """Create a new teacher."""

        teacher = TeacherModel(
            institutional_code=data.institutional_code,
            department_id=data.department_id,
            contract_type=data.contract_type,
            user_id=data.user_id,
        )

        self.db.add(teacher)
        self.db.commit()
        self.db.refresh(teacher)

        return teacher_to_dict(teacher)

    async def get_all(
        self,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        """Get all teachers with optional pagination and search."""

        query = (
            self.db.query(TeacherModel)
            .outerjoin(TeacherModel.user)
            .options(joinedload(TeacherModel.user))
        )

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    TeacherModel.institutional_code.ilike(pattern),
                    TeacherModel.contract_type.ilike(pattern),
                    UserModel.name.ilike(pattern),
                    UserModel.email.ilike(pattern),
                )
            )

        total = query.count()

        teachers = (
            query.order_by(TeacherModel.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        return [teacher_to_dict(t) for t in teachers], total

    async def get_by_id(self, teacher_id: int) -> dict | None:
        """Get a teacher by ID."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        return teacher_to_dict(teacher)

    async def get_by_institutional_code(self, institutional_code: str) -> dict | None:
        """Get a teacher by institutional code."""

        teacher = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.institutional_code == institutional_code)
            .first()
        )

        if not teacher:
            return None

        return teacher_to_dict(teacher)

    async def get_by_institutional_codes(self, codes: list[str]) -> list[dict]:
        """Get existing teachers by a list of institutional codes."""

        teachers = (
            self.db.query(TeacherModel)
            .filter(TeacherModel.institutional_code.in_(codes))
            .all()
        )

        return [teacher_to_dict(t) for t in teachers]

    async def delete(self, teacher_id: int) -> dict | None:
        """Delete a teacher by ID."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        teacher_dict = teacher_to_dict(teacher)
        self.db.delete(teacher)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError(
                "No se puede eliminar el profesor porque tiene grupos académicos asociados"
            )

        return teacher_dict

    async def update(self, teacher_id: int, data: TeacherUpdate) -> dict | None:
        """Update a teacher's fields."""

        teacher = (
            self.db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()
        )

        if not teacher:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(teacher, field, value)

        self.db.commit()
        self.db.refresh(teacher)

        return teacher_to_dict(teacher)


def get_teachers_repository(db: Annotated[Session, Depends(get_db)]):
    """Get teachers repository"""

    return TeachersRepository(db)
