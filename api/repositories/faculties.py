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

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get all faculties with pagination and optional search filter."""

        query = self.db.query(FacultyModel)

        if search:
            term = search.strip()
            if term:
                like_term = f"%{term}%"
                query = query.filter(
                    (FacultyModel.name.ilike(like_term))
                    | (FacultyModel.code.ilike(like_term))
                )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        faculties = (
            query.order_by(FacultyModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "items": [faculty_to_dict(f) for f in faculties],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

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
