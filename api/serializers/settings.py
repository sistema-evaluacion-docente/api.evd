"""Serializer for SettingModel and SettingHistoryModel to dictionary representation."""

from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel
from api.schemas.setting import SettingScope


def setting_to_dict(setting: SettingModel) -> dict:
    """Convert a SettingModel instance to a dictionary representation."""

    user = setting.changed_by_user
    department = setting.department

    return {
        "id": setting.id,
        "key": setting.key,
        "value": setting.value,
        "value_type": setting.value_type,
        "description": setting.description,
        "department_id": setting.department_id,
        "department_name": department.name if department else None,
        "scope": (
            SettingScope.DEPARTMENT.value
            if setting.department_id
            else SettingScope.GLOBAL.value
        ),
        "changed_by": setting.changed_by,
        "changed_by_name": user.name if user else None,
        "changed_by_avatar_url": user.avatar_url if user else None,
        "effective_from": setting.effective_from,
        "created_at": setting.created_at,
        "updated_at": setting.updated_at,
    }


def setting_history_to_dict(history: SettingHistoryModel) -> dict:
    """Convert a SettingHistoryModel instance to a dictionary representation."""

    user = history.changed_by_user

    return {
        "id": history.id,
        "key": history.key,
        "old_value": history.old_value,
        "new_value": history.new_value,
        "department_id": history.department_id,
        "changed_by": history.changed_by,
        "changed_by_name": user.name if user else None,
        "changed_by_avatar_url": user.avatar_url if user else None,
        "change_reason": history.change_reason,
        "changed_at": history.changed_at,
    }
