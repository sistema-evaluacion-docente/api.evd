"""Seed script to create default settings.

Usage:
    python scripts/seed_settings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal
from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel

_ = (SettingHistoryModel,)


DEFAULT_SETTINGS: list[dict[str, str]] = [
    {
        "key": "improvement_plan.score_threshold",
        "value": "3.5",
        "value_type": "NUMBER",
        "description": (
            "Promedio mínimo requerido. Menor a este valor activan un plan de mejoramiento."
        ),
    },
]


def seed_settings() -> None:
    db = SessionLocal()
    try:
        for data in DEFAULT_SETTINGS:
            existing = (
                db.query(SettingModel).filter(SettingModel.key == data["key"]).first()
            )

            if not existing:
                setting = SettingModel(
                    key=data["key"],
                    value=data["value"],
                    value_type=data["value_type"],
                    description=data["description"],
                )
                db.add(setting)
                print(f"  Created: {data['key']} = {data['value']}")
            else:
                print(f"  Skipped (already exists): {data['key']}")

        db.commit()
        print("Seeding complete: default settings are ready.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_settings()
