"""
Settings repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel
from api.schemas.setting import SettingCreate, SettingUpdate
from api.serializers.settings import setting_history_to_dict, setting_to_dict


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: SettingCreate) -> dict:
        setting = SettingModel(
            key=data.key,
            value=data.value,
            value_type=data.value_type,
            description=data.description,
        )

        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)

        return setting_to_dict(setting)

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        query = self.db.query(SettingModel)

        if search:
            term = search.strip()
            if term:
                like_term = f"%{term}%"
                query = query.filter(
                    or_(
                        SettingModel.key.ilike(like_term),
                        SettingModel.description.ilike(like_term),
                    )
                )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        settings = (
            query.order_by(SettingModel.key.asc()).offset(offset).limit(limit).all()
        )

        return {
            "items": [setting_to_dict(s) for s in settings],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_id(self, setting_id: int) -> dict | None:
        setting = (
            self.db.query(SettingModel).filter(SettingModel.id == setting_id).first()
        )

        if not setting:
            return None

        return setting_to_dict(setting)

    async def get_by_key(self, key: str) -> dict | None:
        setting = self.db.query(SettingModel).filter(SettingModel.key == key).first()

        if not setting:
            return None

        return setting_to_dict(setting)

    async def update(
        self, setting_id: int, data: SettingUpdate, changed_by: str | None = None
    ) -> dict | None:
        setting = (
            self.db.query(SettingModel).filter(SettingModel.id == setting_id).first()
        )

        if not setting:
            return None

        old_value = setting.value

        setting.value = data.value
        setting.changed_by = changed_by

        self.db.commit()
        self.db.refresh(setting)

        return {
            "setting": setting_to_dict(setting),
            "old_value": old_value,
        }

    async def delete(self, setting_id: int) -> dict | None:
        setting = (
            self.db.query(SettingModel).filter(SettingModel.id == setting_id).first()
        )

        if not setting:
            return None

        setting_dict = setting_to_dict(setting)
        self.db.delete(setting)
        self.db.commit()

        return setting_dict

    async def add_history(
        self,
        key: str,
        old_value: str | None,
        new_value: str,
        changed_by: str | None = None,
        change_reason: str | None = None,
    ) -> dict:
        history = SettingHistoryModel(
            key=key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            change_reason=change_reason,
        )

        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        return setting_history_to_dict(history)

    async def get_history(
        self,
        setting_id: int | None = None,
        key: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        query = self.db.query(SettingHistoryModel)

        if key:
            query = query.filter(SettingHistoryModel.key == key)
        elif setting_id is not None:
            setting = (
                self.db.query(SettingModel)
                .filter(SettingModel.id == setting_id)
                .first()
            )
            if setting:
                query = query.filter(SettingHistoryModel.key == setting.key)

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        history = (
            query.order_by(SettingHistoryModel.changed_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "items": [setting_history_to_dict(h) for h in history],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }


def get_settings_repository(db: Annotated[Session, Depends(get_db)]):
    return SettingsRepository(db)
