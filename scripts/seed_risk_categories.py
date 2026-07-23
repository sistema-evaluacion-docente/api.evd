"""Seed script to populate risk_levels and pedagogical_categories tables.

Usage:
    python scripts/seed_risk_categories.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal
from api.models.pedagogical_category import PedagogicalCategoryModel
from api.models.risk_level import RiskLevelModel

DEFAULT_RISK_LEVELS: list[dict[str, str]] = [
    {
        "name": "BAJO",
        "description": "Riesgo bajo para el aprendizaje",
        "color_hex": "#22c55e",
    },
    {
        "name": "MEDIO",
        "description": "Riesgo medio para el aprendizaje",
        "color_hex": "#f59e0b",
    },
    {
        "name": "ALTO",
        "description": "Riesgo alto para el aprendizaje",
        "color_hex": "#ef4444",
    },
]

# TODO: Update the default categories with meaningful descriptions and colors
DEFAULT_CATEGORIES: list[dict[str, str]] = [
    {
        "name": "LABEL_0",
        "description": "Categoría pedagógica 0",
        "color_hex": "#3b82f6",
    },
    {
        "name": "LABEL_1",
        "description": "Categoría pedagógica 1",
        "color_hex": "#8b5cf6",
    },
    {
        "name": "LABEL_2",
        "description": "Categoría pedagógica 2",
        "color_hex": "#06b6d4",
    },
    {
        "name": "LABEL_3",
        "description": "Categoría pedagógica 3",
        "color_hex": "#f97316",
    },
    {
        "name": "LABEL_4",
        "description": "Categoría pedagógica 4",
        "color_hex": "#6b7280",
    },
]


def seed_risk_levels() -> None:
    db = SessionLocal()
    try:
        for data in DEFAULT_RISK_LEVELS:
            existing = (
                db.query(RiskLevelModel)
                .filter(RiskLevelModel.name == data["name"])
                .first()
            )
            if not existing:
                db.add(RiskLevelModel(**data))
                print(f"  Created risk level: {data['name']}")
            else:
                print(f"  Skipped (already exists): {data['name']}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_categories() -> None:
    db = SessionLocal()
    try:
        for data in DEFAULT_CATEGORIES:
            existing = (
                db.query(PedagogicalCategoryModel)
                .filter(PedagogicalCategoryModel.name == data["name"])
                .first()
            )
            if not existing:
                db.add(PedagogicalCategoryModel(**data))
                print(f"  Created category: {data['name']}")
            else:
                print(f"  Skipped (already exists): {data['name']}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding risk levels...")
    seed_risk_levels()
    print("Seeding pedagogical categories...")
    seed_categories()
    print("Seeding complete: risk levels and pedagogical categories are ready.")
