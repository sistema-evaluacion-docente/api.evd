"""Serializer for SettingModel and SettingHistoryModel to dictionary representation."""

from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel


def setting_to_dict(setting: SettingModel) -> dict:
    user = setting.changed_by_user

    return {
        "id": setting.id,
        "key": setting.key,
        "value": setting.value,
        "value_type": setting.value_type,
        "description": setting.description,
        "changed_by": setting.changed_by,
        "changed_by_name": user.name if user else None,
        "changed_by_avatar_url": user.avatar_url if user else None,
        "effective_from": setting.effective_from,
        "created_at": setting.created_at,
        "updated_at": setting.updated_at,
    }


def setting_history_to_dict(history: SettingHistoryModel) -> dict:
    user = history.changed_by_user

    return {
        "id": history.id,
        "key": history.key,
        "old_value": history.old_value,
        "new_value": history.new_value,
        "changed_by": history.changed_by,
        "changed_by_name": user.name if user else None,
        "changed_by_avatar_url": user.avatar_url if user else None,
        "change_reason": history.change_reason,
        "changed_at": history.changed_at,
    }
