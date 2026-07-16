"""
Directors repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.user import UserModel
from api.schemas.director import DirectorRecordCreate, DirectorUpdate
from api.serializers.directors import director_to_dict


class DirectorsRepository:
    """Directors repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: DirectorRecordCreate) -> dict:
        """Create a new director."""

        director = DirectorsModel(
            user_id=data.user_id,
            department_id=data.department_id,
        )

        self.db.add(director)
        self.db.commit()
        self.db.refresh(director)

        return director_to_dict(director)

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get all directors with pagination and optional search filter."""

        query = self.db.query(DirectorsModel)

        if search:
            term = search.strip()
            if term:
                like_term = f"%{term}%"

                query = (
                    query.join(UserModel, UserModel.id == DirectorsModel.user_id)
                    .join(
                        DepartmentModel,
                        DepartmentModel.id == DirectorsModel.department_id,
                    )
                    .filter(
                        (UserModel.name.ilike(like_term))
                        | (UserModel.email.ilike(like_term))
                        | (DepartmentModel.name.ilike(like_term))
                        | (DepartmentModel.code.ilike(like_term))
                    )
                )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        directors = (
            query.order_by(DirectorsModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        director_dicts = [director_to_dict(d) for d in directors]

        if director_dicts:
            director_ids = [d["id"] for d in director_dicts]

            enriched = (
                self.db.query(
                    DirectorsModel.id,
                    UserModel.id.label("user_id"),
                    UserModel.name,
                    UserModel.avatar_url,
                    DepartmentModel.id.label("dept_id"),
                    DepartmentModel.name.label("dept_name"),
                )
                .select_from(DirectorsModel)
                .join(UserModel, UserModel.id == DirectorsModel.user_id)
                .join(
                    DepartmentModel, DepartmentModel.id == DirectorsModel.department_id
                )
                .filter(DirectorsModel.id.in_(director_ids))
                .all()
            )

            enriched_map = {
                row.id: {
                    "user": {
                        "id": row.user_id,
                        "name": row.name,
                        "avatar_url": row.avatar_url,
                    },
                    "department": {
                        "id": row.dept_id,
                        "name": row.dept_name,
                    },
                }
                for row in enriched
            }

            for d in director_dicts:
                d["user"] = enriched_map.get(d["id"], {}).get("user")
                d["department"] = enriched_map.get(d["id"], {}).get("department")

        return {
            "items": director_dicts,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_id(self, director_id: int) -> dict | None:
        """Get a director by ID."""

        director = (
            self.db.query(DirectorsModel)
            .filter(DirectorsModel.id == director_id)
            .first()
        )

        if not director:
            return None

        director_dict = director_to_dict(director)

        enriched = (
            self.db.query(
                UserModel.id.label("user_id"),
                UserModel.name,
                UserModel.avatar_url,
                DepartmentModel.id.label("dept_id"),
                DepartmentModel.name.label("dept_name"),
            )
            .select_from(DirectorsModel)
            .join(UserModel, UserModel.id == DirectorsModel.user_id)
            .join(DepartmentModel, DepartmentModel.id == DirectorsModel.department_id)
            .filter(DirectorsModel.id == director_id)
            .first()
        )

        if enriched:
            director_dict["user"] = {
                "id": enriched.user_id,
                "name": enriched.name,
                "avatar_url": enriched.avatar_url,
            }
            director_dict["department"] = {
                "id": enriched.dept_id,
                "name": enriched.dept_name,
            }

        return director_dict

    async def get_by_department_id(self, department_id: int) -> dict | None:
        """Get the director of a department."""

        director = (
            self.db.query(DirectorsModel)
            .filter(
                DirectorsModel.department_id == department_id,
                DirectorsModel.active == True,
            )
            .first()
        )

        if not director:
            return None

        return director_to_dict(director)

    async def get_by_user_id(self, user_id: int) -> dict | None:
        """Get director record by user ID."""

        director = (
            self.db.query(DirectorsModel)
            .filter(
                DirectorsModel.user_id == user_id,
                DirectorsModel.active == True,
            )
            .first()
        )

        if not director:
            return None

        return director_to_dict(director)

    async def update(self, director_id: int, data: DirectorUpdate) -> dict | None:
        """Update a director's fields."""

        director = (
            self.db.query(DirectorsModel)
            .filter(DirectorsModel.id == director_id)
            .first()
        )

        if not director:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(director, field, value)

        self.db.commit()
        self.db.refresh(director)

        return director_to_dict(director)

    async def delete(self, director_id: int) -> dict | None:
        """Delete a director."""

        director = (
            self.db.query(DirectorsModel)
            .filter(DirectorsModel.id == director_id)
            .first()
        )

        if not director:
            return None

        director_dict = director_to_dict(director)
        self.db.delete(director)
        self.db.commit()

        return director_dict

    async def assign_director(self, user_id: int, department_id: int) -> dict:
        """Assign a director to a department, replacing any existing director."""

        existing = (
            self.db.query(DirectorsModel)
            .filter(DirectorsModel.department_id == department_id)
            .first()
        )

        if existing:
            existing.user_id = user_id
            existing.active = True
            self.db.commit()
            self.db.refresh(existing)
            return director_to_dict(existing)

        director = DirectorsModel(
            user_id=user_id,
            department_id=department_id,
        )

        self.db.add(director)
        self.db.commit()
        self.db.refresh(director)

        return director_to_dict(director)


def get_directors_repository(db: Annotated[Session, Depends(get_db)]):
    """Get directors repository"""

    return DirectorsRepository(db)
