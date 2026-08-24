"""
Program repository module.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.program import ProgramModel
from api.repositories.base import BaseRepository
from api.schemas.program import ProgramCreate, ProgramFilters, ProgramUpdate


class ProgramsRepository(BaseRepository[ProgramModel]):
    """Repository for Program operations."""

    def __init__(self, db: Annotated[Session, Depends(get_db)]):
        super().__init__(ProgramModel, db)

    def get_by_code(self, code: str) -> ProgramModel | None:
        """Get a program by code."""

        return self.db.query(ProgramModel).filter(ProgramModel.code == code).first()

    def search(
        self, filters: ProgramFilters, pagination: PaginationParams
    ) -> tuple[list[ProgramModel], int]:
        """Search programs with filters and pagination."""

        query = self.db.query(ProgramModel)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                (ProgramModel.name.ilike(search_term))
                | (ProgramModel.code.ilike(search_term))
            )

        if filters.active is not None:
            query = query.filter(ProgramModel.active == filters.active)

        return self.paginate(query, pagination)

    def create_program(self, data: ProgramCreate) -> ProgramModel:
        """Create a new program."""

        program = ProgramModel(**data.model_dump())
        self.db.add(program)
        self.db.commit()
        self.db.refresh(program)
        return program

    def update_program(
        self, program: ProgramModel, data: ProgramUpdate
    ) -> ProgramModel:
        """Update a program."""

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(program, key, value)

        self.db.commit()
        self.db.refresh(program)
        return program

    def delete_program(self, program: ProgramModel) -> None:
        """Delete a program."""

        self.db.delete(program)
        self.db.commit()


def get_programs_repository(
    db: Annotated[Session, Depends(get_db)],
) -> ProgramsRepository:
    """Get programs repository instance."""

    return ProgramsRepository(db)
