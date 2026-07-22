"""Repository for setting-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel
from api.repositories.base import BaseRepository
from api.schemas.setting import SettingFilters


class SettingsRepository(BaseRepository[SettingModel]):
    """Repository for setting-related database operations."""

    def __init__(self, db: Session):
        super().__init__(SettingModel, db)

    def get_by_key(self, key: str) -> SettingModel | None:
        """Get a setting by key."""

        return self.db.query(SettingModel).filter(SettingModel.key == key).first()

    def search(
        self,
        filters: SettingFilters,
        pagination: PaginationParams,
    ) -> tuple[list[SettingModel], int]:
        """Search for settings based on filters and pagination parameters."""

        query = self.db.query(SettingModel)

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

        query = query.order_by(SettingModel.key.asc())

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
    ) -> tuple[list[SettingHistoryModel], int]:
        """Get setting history with optional filters and pagination."""

        query = self.db.query(SettingHistoryModel)

        if key:
            query = query.filter(SettingHistoryModel.key == key)

        query = query.order_by(SettingHistoryModel.changed_at.desc())

        if pagination:
            return self.paginate(query, pagination)

        items = query.all()
        return items, len(items)


def get_settings_repository(db: Annotated[Session, Depends(get_db)]):
    """Dependency injection for SettingsRepository."""

    return SettingsRepository(db)
