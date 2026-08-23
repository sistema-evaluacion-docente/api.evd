"""Seed script to create the initial departments (departamentos) of the UFPS.

Each department is linked to its faculty via the faculty `code` (see
scripts/seed_faculties.py), so faculties must be seeded first.

Usage:
    python scripts/seed_departments.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal
from api.models.department import DepartmentModel
from api.models.faculty import FacultyModel

DEFAULT_DEPARTMENTS: list[dict[str, str]] = [
    # Facultad de Ingeniería (FI)
    {
        "code": "48",
        "name": "Diseño Mecánico, Materiales, Procesos y Térmicas (Mecánica)",
        "faculty_code": "FI",
    },
    {
        "code": "49",
        "name": "Electricidad y Electrónica",
        "faculty_code": "FI",
    },
    {
        "code": "51",
        "name": "Geotecnia y Minería",
        "faculty_code": "FI",
    },
    {
        "code": "52",
        "name": "Sistemas e Informática",
        "faculty_code": "FI",
    },
    {
        "code": "62",
        "name": "Construcción Civil y Vías",
        "faculty_code": "FI",
    },
    # Facultad de Ciencias Básicas (FCB)
    {"code": "54", "name": "Química", "faculty_code": "FCB"},
    {"code": "55", "name": "Biología", "faculty_code": "FCB"},
    {
        "code": "56",
        "name": "Matemáticas y Estadística",
        "faculty_code": "FCB",
    },
    {"code": "60", "name": "Física", "faculty_code": "FCB"},
    # Facultad de Ciencias de la Salud (FCS)
    {
        "code": "53",
        "name": "Atención Clínica y Rehabilitación",
        "faculty_code": "FCS",
    },
    {
        "code": "61",
        "name": "Promoción, Protección y Gestión de la Salud",
        "faculty_code": "FCS",
    },
    # Facultad de Ciencias Empresariales (FCE)
    {
        "code": "45",
        "name": "Ciencias Contables y Financieras",
        "faculty_code": "FCE",
    },
    {
        "code": "46",
        "name": "Administración de Empresas",
        "faculty_code": "FCE",
    },
    {
        "code": "47",
        "name": "Estudios Socioeconómicos y Comercio Internacional",
        "faculty_code": "FCE",
    },
    # Facultad de Ciencias Agrarias y del Ambiente (FCAA)
    {
        "code": "57",
        "name": "Ciencias Agrícolas y de la Tierra",
        "faculty_code": "FCAA",
    },
    {
        "code": "58",
        "name": "Ciencias Pecuarias y del Medio Ambiente",
        "faculty_code": "FCAA",
    },
    {
        "code": "59",
        "name": "Fluidos y Texturas (Procesos Agroindustriales)",
        "faculty_code": "FCAA",
    },
    # Facultad de Educación, Artes y Humanidades (FEAH)
    {
        "code": "42",
        "name": "Pedagogía, Andragogía, Comunicación y Multimedios",
        "faculty_code": "FEAH",
    },
    {
        "code": "43",
        "name": "Arquitectura, Diseño y Urbanismo",
        "faculty_code": "FEAH",
    },
    {
        "code": "63",
        "name": "Humanidades, Artes y Ciencias Sociales",
        "faculty_code": "FEAH",
    },
    {
        "code": "64",
        "name": "Derecho y Ciencias Políticas",
        "faculty_code": "FEAH",
    },
]


def seed_departments() -> None:
    db = SessionLocal()
    try:
        faculties_by_code = {
            faculty.code: faculty for faculty in db.query(FacultyModel).all()
        }

        for data in DEFAULT_DEPARTMENTS:
            faculty = faculties_by_code.get(data["faculty_code"])
            if not faculty:
                print(
                    f"  Skipped: {data['name']} "
                    f"(faculty '{data['faculty_code']}' not found, "
                    "run seed_faculties.py first)"
                )
                continue

            existing = (
                db.query(DepartmentModel)
                .filter(
                    (DepartmentModel.code == data["code"])
                    | (DepartmentModel.name == data["name"])
                )
                .first()
            )

            if not existing:
                department = DepartmentModel(
                    code=data["code"],
                    name=data["name"],
                    faculty_id=faculty.id,
                    active=True,
                )
                db.add(department)
                print(f"  Created: {data['code']} - {data['name']}")
            else:
                print(f"  Skipped (already exists): {data['name']}")

        db.commit()
        print("Seeding complete: default departments are ready.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_departments()
