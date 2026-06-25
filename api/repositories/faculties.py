"""
Faculties repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.faculty import FacultyModel
from api.schemas.faculty import FacultyCreate, FacultyUpdate
from api.serializers.faculties import faculty_to_dict


class FacultiesRepository:
    """Faculties repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: FacultyCreate) -> dict:
        """Create a new faculty."""

        faculty = FacultyModel(
            name=data.name,
            code=data.code,
        )

        self.db.add(faculty)
        self.db.commit()
        self.db.refresh(faculty)

        return faculty_to_dict(faculty)

    async def get_all(self) -> list[dict]:
        """Get all faculties ordered by creation date descending."""

        faculties = (
            self.db.query(FacultyModel)
            .order_by(FacultyModel.created_at.desc())
            .all()
        )

        return [faculty_to_dict(f) for f in faculties]

    async def get_by_id(self, faculty_id: int) -> dict | None:
        """Get a faculty by ID."""

        faculty = (
            self.db.query(FacultyModel)
            .filter(FacultyModel.id == faculty_id)
            .first()
        )

        if not faculty:
            return None

        return faculty_to_dict(faculty)

    async def get_by_code(self, code: str) -> dict | None:
        """Get a faculty by code."""

        faculty = (
            self.db.query(FacultyModel).filter(FacultyModel.code == code).first()
        )

        if not faculty:
            return None

        return faculty_to_dict(faculty)

    async def update(self, faculty_id: int, data: FacultyUpdate) -> dict | None:
        """Update a faculty's fields."""

        faculty = (
            self.db.query(FacultyModel)
            .filter(FacultyModel.id == faculty_id)
            .first()
        )

        if not faculty:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(faculty, field, value)

        self.db.commit()
        self.db.refresh(faculty)

        return faculty_to_dict(faculty)


def get_faculties_repository(db: Annotated[Session, Depends(get_db)]):
    """Get faculties repository"""

    return FacultiesRepository(db)
