"""Repository for Director entity."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.user import UserModel
from api.repositories.base import BaseRepository
from api.schemas.director import DirectorFilters, DirectorUpdate


class DirectorsRepository(BaseRepository[DirectorsModel]):
    """Repository to manage DirectorsModel."""

    def __init__(self, db: Annotated[Session, Depends(get_db)]):
        super().__init__(DirectorsModel, db)

    def get_by_department_id(self, department_id: int) -> DirectorsModel | None:
        """Get director active by department_id."""

        return (
            self.db.query(DirectorsModel)
            .filter(
                DirectorsModel.department_id == department_id,
                DirectorsModel.active == True,
            )
            .first()
        )

    def get_by_institutional_code(
        self, institutional_code: str
    ) -> DirectorsModel | None:
        """Get a director by institutional code."""

        return (
            self.db.query(DirectorsModel)
            .filter(DirectorsModel.institutional_code == institutional_code)
            .first()
        )

    def get_by_user_id(self, user_id: int) -> DirectorsModel | None:
        """Get director activo by user_id."""

        return (
            self.db.query(DirectorsModel)
            .filter(
                DirectorsModel.user_id == user_id,
                DirectorsModel.active == True,
            )
            .first()
        )

    def search(
        self, filters: DirectorFilters, pagination: PaginationParams
    ) -> tuple[list[DirectorsModel], int]:
        """Search directors with filters and pagination."""

        query = (
            self.db.query(DirectorsModel)
            .join(UserModel, DirectorsModel.user_id == UserModel.id)
            .join(DepartmentModel, DirectorsModel.department_id == DepartmentModel.id)
        )

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    UserModel.name.ilike(search_term),
                    UserModel.email.ilike(search_term),
                    DepartmentModel.name.ilike(search_term),
                    DepartmentModel.code.ilike(search_term),
                )
            )

        if filters.active is not None:
            query = query.filter(DirectorsModel.active == filters.active)

        return self.paginate(query, pagination)

    def update_director(
        self, director: DirectorsModel, data: DirectorUpdate
    ) -> DirectorsModel:
        """Actualizar director."""
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(director, key, value)
        self.db.commit()
        self.db.refresh(director)
        return director

    def delete_director(self, director: DirectorsModel) -> None:
        """Delete director."""

        self.db.delete(director)
        self.db.commit()

    def assign_director(self, user_id: int, department_id: int) -> DirectorsModel:
        """
        Asign a user as director to a department.If the user is already
        a director of another department, raise an error. If the department already
        has a director, update the existing director with the new user_id.
        """

        existing_user_director = (
            self.db.query(DirectorsModel)
            .filter(DirectorsModel.user_id == user_id)
            .first()
        )

        if (
            existing_user_director
            and existing_user_director.department_id != department_id
        ):
            raise ValueError("Este usuario ya es director de otro departamento")

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
            return existing

        director = DirectorsModel(
            user_id=user_id,
            department_id=department_id,
        )
        self.db.add(director)
        self.db.commit()
        self.db.refresh(director)
        return director


def get_directors_repository(
    db: Annotated[Session, Depends(get_db)],
) -> DirectorsRepository:
    """Dependency to get DirectorsRepository."""

    return DirectorsRepository(db)
