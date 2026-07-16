"""
Departments repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.user import UserModel
from api.schemas.department import DepartmentCreate, DepartmentUpdate
from api.serializers.departments import department_to_dict


class DepartmentsRepository:
    """Departments repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: DepartmentCreate) -> dict:
        """Create a new department."""

        department = DepartmentModel(
            code=data.code,
            name=data.name,
            faculty_id=data.faculty_id,
        )

        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)

        return department_to_dict(department)

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get all departments with pagination and optional search filter."""

        query = self.db.query(DepartmentModel)

        if search:
            term = search.strip()
            if term:
                like_term = f"%{term}%"
                query = query.filter(
                    (DepartmentModel.name.ilike(like_term))
                    | (DepartmentModel.code.ilike(like_term))
                )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        departments = (
            query.order_by(DepartmentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        department_dicts = [department_to_dict(d) for d in departments]

        if department_dicts:
            department_ids = [d["id"] for d in department_dicts]

            directors = (
                self.db.query(
                    UserModel.id,
                    UserModel.name,
                    UserModel.avatar_url,
                    DirectorsModel.department_id,
                )
                .select_from(UserModel)
                .join(DirectorsModel, DirectorsModel.user_id == UserModel.id)
                .filter(
                    DirectorsModel.department_id.in_(department_ids),
                    DirectorsModel.active == True,
                )
                .all()
            )

            directors_by_dept = {
                d.department_id: {
                    "id": d.id,
                    "name": d.name,
                    "avatar_url": d.avatar_url,
                }
                for d in directors
            }

            for dept_dict in department_dicts:
                dept_dict["director"] = directors_by_dept.get(dept_dict["id"])

        return {
            "items": department_dicts,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_id(self, department_id: int) -> dict | None:
        """Get a department by ID."""

        department = (
            self.db.query(DepartmentModel)
            .filter(DepartmentModel.id == department_id)
            .first()
        )

        if not department:
            return None

        dept_dict = department_to_dict(department)

        director_row = (
            self.db.query(
                UserModel.id,
                UserModel.name,
                UserModel.avatar_url,
            )
            .select_from(UserModel)
            .join(DirectorsModel, DirectorsModel.user_id == UserModel.id)
            .filter(
                DirectorsModel.department_id == department_id,
                DirectorsModel.active == True,
            )
            .first()
        )

        if director_row:
            dept_dict["director"] = {
                "id": director_row.id,
                "name": director_row.name,
                "avatar_url": director_row.avatar_url,
            }

        return dept_dict

    async def get_by_code(self, code: str) -> dict | None:
        """Get a department by code."""

        department = (
            self.db.query(DepartmentModel).filter(DepartmentModel.code == code).first()
        )

        if not department:
            return None

        return department_to_dict(department)

    async def update(self, department_id: int, data: DepartmentUpdate) -> dict | None:
        """Update a department's fields."""

        department = (
            self.db.query(DepartmentModel)
            .filter(DepartmentModel.id == department_id)
            .first()
        )

        if not department:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(department, field, value)

        self.db.commit()
        self.db.refresh(department)

        return department_to_dict(department)


def get_departments_repository(db: Annotated[Session, Depends(get_db)]):
    """Get departments repository"""

    return DepartmentsRepository(db)
