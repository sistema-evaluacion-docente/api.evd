"""
Academic groups repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.schemas.academic_group import AcademicGroupCreate, AcademicGroupUpdate
from api.serializers.academic_groups import academic_group_to_dict


class AcademicGroupsRepository:
    """Academic groups repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: AcademicGroupCreate) -> dict:
        """Create a new academic group."""

        group = AcademicGroupModel(
            course_id=data.course_id,
            teacher_id=data.teacher_id,
            academic_period_id=data.academic_period_id,
            group_name=data.group_name,
        )

        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)

        return academic_group_to_dict(group)

    async def get_all(self) -> list[dict]:
        """Get all academic groups ordered by creation date descending."""

        groups = (
            self.db.query(AcademicGroupModel)
            .order_by(AcademicGroupModel.created_at.desc())
            .all()
        )

        return [academic_group_to_dict(g) for g in groups]

    async def get_by_id(self, group_id: int) -> dict | None:
        """Get an academic group by ID."""

        group = (
            self.db.query(AcademicGroupModel)
            .filter(AcademicGroupModel.id == group_id)
            .first()
        )

        if not group:
            return None

        return academic_group_to_dict(group)

    async def get_by_teacher_and_period(
        self, teacher_id: int, academic_period_id: int
    ) -> list[dict]:
        """Get all groups for a teacher in a given period."""

        groups = (
            self.db.query(AcademicGroupModel)
            .filter(
                AcademicGroupModel.teacher_id == teacher_id,
                AcademicGroupModel.academic_period_id == academic_period_id,
            )
            .all()
        )

        return [academic_group_to_dict(g) for g in groups]

    async def get_by_course_teacher_period(
        self, course_id: int, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Get a group by the combination of course, teacher and period."""

        group = (
            self.db.query(AcademicGroupModel)
            .filter(
                AcademicGroupModel.course_id == course_id,
                AcademicGroupModel.teacher_id == teacher_id,
                AcademicGroupModel.academic_period_id == academic_period_id,
            )
            .first()
        )

        if not group:
            return None

        return academic_group_to_dict(group)

    async def update(self, group_id: int, data: AcademicGroupUpdate) -> dict | None:
        """Update an academic group's fields."""

        group = (
            self.db.query(AcademicGroupModel)
            .filter(AcademicGroupModel.id == group_id)
            .first()
        )

        if not group:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(group, field, value)

        self.db.commit()
        self.db.refresh(group)

        return academic_group_to_dict(group)


def get_academic_groups_repository(db: Annotated[Session, Depends(get_db)]):
    """Get academic groups repository"""

    return AcademicGroupsRepository(db)
