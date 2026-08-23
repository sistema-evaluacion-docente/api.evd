"""Seed script to create the initial faculties (facultades) of the UFPS.

Usage:
    python scripts/seed_faculties.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal
from api.models.faculty import FacultyModel

DEFAULT_FACULTIES: list[dict[str, str]] = [
    {"name": "Educación, Artes y Humanidades", "code": "FEAH"},
    {"name": "Ciencias de la Salud", "code": "FCS"},
    {"name": "Ciencias Empresariales", "code": "FCE"},
    {"name": "Ciencias Básicas", "code": "FCB"},
    {"name": "Ciencias Agrarias y del Ambiente", "code": "FCAA"},
    {"name": "Ingeniería", "code": "FI"},
]


def seed_faculties() -> None:
    db = SessionLocal()
    try:
        for data in DEFAULT_FACULTIES:
            existing = (
                db.query(FacultyModel)
                .filter(
                    (FacultyModel.code == data["code"])
                    | (FacultyModel.name == data["name"])
                )
                .first()
            )

            if not existing:
                faculty = FacultyModel(
                    name=data["name"],
                    code=data["code"],
                    active=True,
                )
                db.add(faculty)
                print(f"  Created: {data['name']} ({data['code']})")
            else:
                print(f"  Skipped (already exists): {data['name']}")

        db.commit()
        print("Seeding complete: default faculties are ready.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_faculties()
