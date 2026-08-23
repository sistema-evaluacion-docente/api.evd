"""Repository for setting-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, contains_eager, joinedload

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel
from api.models.user import UserModel
from api.repositories.base import BaseRepository
from api.schemas.setting import SettingFilters


class SettingsRepository(BaseRepository[SettingModel]):
    """Repository for setting-related database operations."""

    def __init__(self, db: Session):
        super().__init__(SettingModel, db)

    def get(self, setting_id: int) -> SettingModel | None:
        """Get a setting by ID with its department and changed-by user loaded."""

        return (
            self.db.query(SettingModel)
            .options(
                joinedload(SettingModel.changed_by_user),
                joinedload(SettingModel.department),
            )
            .filter(SettingModel.id == setting_id)
            .first()
        )

    def get_by_key(
        self, key: str, department_id: int | None = None
    ) -> SettingModel | None:
        """Get the setting of exactly one scope: a department's, or the global one."""

        query = (
            self.db.query(SettingModel)
            .options(
                joinedload(SettingModel.changed_by_user),
                joinedload(SettingModel.department),
            )
            .filter(SettingModel.key == key)
        )

        if department_id is None:
            query = query.filter(SettingModel.department_id.is_(None))
        else:
            query = query.filter(SettingModel.department_id == department_id)

        return query.first()

    def resolve(
        self, key: str, department_id: int | None = None
    ) -> SettingModel | None:
        """Get the setting that applies to a department.

        The department's own value wins; the institutional one is the fallback
        for a department that has not overridden the key.
        """

        if department_id is not None:
            scoped = self.get_by_key(key, department_id)

            if scoped:
                return scoped

        return self.get_by_key(key)

    def search(
        self,
        filters: SettingFilters,
        pagination: PaginationParams,
    ) -> tuple[list[SettingModel], int]:
        """Search for settings within one scope.

        ``filters.department_id`` names that scope — a department, or the
        institutional settings when it is None — and ``include_global`` decides
        whether a department listing carries the institutional values it falls
        back to.
        """

        query = (
            self.db.query(SettingModel)
            .outerjoin(UserModel, UserModel.uid == SettingModel.changed_by)
            .options(
                contains_eager(SettingModel.changed_by_user),
                joinedload(SettingModel.department),
            )
        )

        if filters.department_id is None:
            # No department means the institutional scope, the same as it does
            # in get_by_key and get_history — never "every scope at once".
            query = query.filter(SettingModel.department_id.is_(None))
        else:
            scope = SettingModel.department_id == filters.department_id

            if filters.include_global:
                scope = or_(scope, SettingModel.department_id.is_(None))

            query = query.filter(scope)

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        SettingModel.key.ilike(like_term),
                        SettingModel.description.ilike(like_term),
                    )
                )

        if filters.value_type:
            query = query.filter(SettingModel.value_type == filters.value_type)

        # The institutional value first, then the departments that override it.
        query = query.order_by(
            SettingModel.key.asc(),
            SettingModel.department_id.asc().nullsfirst(),
        )

        return self.paginate(query, pagination)

    def create_setting(self, data: dict) -> SettingModel:
        """Create a new setting."""

        return self.create(data)

    def update_setting(self, setting: SettingModel, data: dict) -> SettingModel:
        """Update a setting's fields."""

        for field, value in data.items():
            if value is not None:
                setattr(setting, field, value)

        self.db.commit()
        self.db.refresh(setting)

        return setting

    def delete_setting(self, setting_id: int) -> SettingModel | None:
        """Delete a setting by ID."""

        setting = self.get(setting_id)

        if not setting:
            return None

        self.db.delete(setting)
        self.db.commit()

        return setting

    def add_history(self, data: dict) -> SettingHistoryModel:
        """Add a setting history entry."""

        history = SettingHistoryModel(**data)
        self.db.add(history)
        self.db.flush()
        return history

    def get_history(
        self,
        key: str | None = None,
        pagination: PaginationParams | None = None,
        department_id: int | None = None,
    ) -> tuple[list[SettingHistoryModel], int]:
        """Get setting history with optional filters and pagination.

        The history is scoped like the setting itself: passing no
        ``department_id`` returns the institutional entries only.
        """

        query = (
            self.db.query(SettingHistoryModel)
            .outerjoin(UserModel, UserModel.uid == SettingHistoryModel.changed_by)
            .options(contains_eager(SettingHistoryModel.changed_by_user))
        )

        if key:
            query = query.filter(SettingHistoryModel.key == key)

        if department_id is None:
            query = query.filter(SettingHistoryModel.department_id.is_(None))
        else:
            query = query.filter(SettingHistoryModel.department_id == department_id)

        query = query.order_by(SettingHistoryModel.changed_at.desc())

        if pagination:
            return self.paginate(query, pagination)

        items = query.all()
        return items, len(items)


def get_settings_repository(db: Annotated[Session, Depends(get_db)]):
    """Dependency injection for SettingsRepository."""

    return SettingsRepository(db)
