"""Seed script to create the initial academic programs (programas) of the UFPS.

The codes are the ``COD_CARRERA`` of the university's academic registry, kept
verbatim — leading zero included, since the column is a string — so a program
read off an evaluation report can be matched by code. Names repeat across codes
(``INGENIERIA CIVIL`` is 011, 111 and 211: the same program under different
registry entries), so ``code`` is the only key used to decide what already
exists.

Usage:
    python scripts/seed_programs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal
from api.models.program import ProgramModel

DEFAULT_PROGRAMS: list[dict[str, str]] = [
    {"code": "009", "name": "INGENIERIA ELECTROMECANICA"},
    {"code": "011", "name": "INGENIERIA CIVIL"},
    {"code": "012", "name": "INGENIERIA MECANICA"},
    {"code": "015", "name": "INGENIERIA DE SISTEMAS"},
    {"code": "016", "name": "INGENIERIA ELECTRONICA"},
    {"code": "018", "name": "INGENIERIA DE MINAS"},
    {"code": "021", "name": "ADMINISTRACION DE EMPRESAS"},
    {"code": "022", "name": "CONTADURIA PUBLICA"},
    {"code": "023", "name": "CONTADURIA PUBLICA"},
    {"code": "025", "name": "ADMINISTRACION DE EMPRESAS"},
    {"code": "031", "name": "LICENCIATURA EN BIOLOGIA Y QUIMICA"},
    {"code": "036", "name": "LICENCIATURA EN MATEMATICAS Y COMPUTACION"},
    {"code": "040", "name": "TECNOLOGIA EN PRODUCCION AGROPECUARIA"},
    {"code": "041", "name": "LICENCIATURA EN EDUCACION BASICA"},
    {"code": "042", "name": "TECNOLOGIA EN OBRAS CIVILES"},
    {"code": "046", "name": "TEC. ADMON. COMERCIAL Y FINANCIERA"},
    {"code": "048", "name": "TECNOLOGIA EN REGENCIA DE FARMACIA"},
    {"code": "050", "name": "ARQUITECTURA"},
    {"code": "051", "name": "PREUNIVERSITARIO"},
    {"code": "052", "name": "PREUNIVERSITARIO"},
    {"code": "053", "name": "PREUNIVERSITARIO"},
    {"code": "054", "name": "PREUNIVERSITARIO"},
    {"code": "055", "name": "PREUNIVERSITARIO"},
    {"code": "056", "name": "PREUNIVERSITARIO"},
    {"code": "058", "name": "ALUMNO CREDITO"},
    {"code": "059", "name": "PREUNIVERSITARIO"},
    {"code": "062", "name": "INGENIERIA DE PRODUCCION AGRICOLA"},
    {"code": "064", "name": "INGENIERIA DE PRODUCCION AGROINDUSTRIAL"},
    {"code": "070", "name": "LICENCIATURA EN INFORMATICA"},
    {"code": "071", "name": "LICENCIATURA EN MATEMATICAS"},
    {"code": "072", "name": "LICENCIATURA EN HUMANIDADES"},
    {"code": "073", "name": "LICENCIATURA EN EDUCACION BASICA ENF EDU. FISICA"},
    {"code": "074", "name": "TECNOLOGIA EN ADMON AGROPECUARIA"},
    {"code": "079", "name": "ADMINISTRACION DE LOS SERVICIOS DE LA SALUD"},
    {"code": "080", "name": "ENFERMERIA"},
    {"code": "085", "name": "LIC. EN EDUCACION BASICA ENF.EN EDUC. ARTISTICA"},
    {"code": "096", "name": "TECNOLOGIA AGROPECUARIA"},
    {"code": "101", "name": "ESPECIALIZACION EN ESTRUCTURAS"},
    {"code": "109", "name": "INGENIERIA ELECTROMECANICA"},
    {"code": "111", "name": "INGENIERIA CIVIL"},
    {"code": "112", "name": "INGENIERIA MECANICA"},
    {"code": "115", "name": "INGENIERIA DE SISTEMAS"},
    {"code": "116", "name": "INGENIERIA ELECTRONICA"},
    {"code": "118", "name": "INGENIERIA DE MINAS"},
    {"code": "119", "name": "INGENIERIA INDUSTRIAL"},
    {"code": "121", "name": "ADMINISTRACION DE EMPRESAS"},
    {"code": "122", "name": "CONTADURIA PUBLICA"},
    {"code": "123", "name": "CONTADURIA PUBLICA"},
    {"code": "125", "name": "ADMINISTRACION DE EMPRESAS"},
    {"code": "126", "name": "COMERCIO INTERNACIONAL"},
    {"code": "130", "name": "LICENCIATURA EN MATEMATICAS E INFORMATICA"},
    {"code": "131", "name": "LICENCIATURA EN BIOLOGIA Y QUIMICA"},
    {"code": "132", "name": "ESPECIALIZACION EN PRACTICA PEDAGOGICA"},
    {"code": "133", "name": "COMUNICACION SOCIAL"},
    {"code": "134", "name": "TRABAJO SOCIAL"},
    {"code": "135", "name": "DERECHO"},
    {"code": "136", "name": "LICENCIATURA EN MATEMATICAS"},
    {"code": "137", "name": "LIC. EN CIENCIAS NATURALES Y EDUCACION AMBIENTAL"},
    {"code": "138", "name": "MAESTRIA EN CIENCIA Y TECNOLOGIA DE MATERIALES"},
    {"code": "139", "name": "MAESTRIA EN PRACTICA PEDAGOGICA"},
    {"code": "142", "name": "TECNOLOGIA EN OBRAS CIVILES"},
    {"code": "143", "name": "TEC. PROF. EN PROCESOS FINANCIEROS - ART"},
    {"code": "146", "name": "TECNOLOGIA COMERCIAL Y FINANCIERA"},
    {"code": "147", "name": "TECNOLOGIA EN ELECTRICIDAD"},
    {"code": "148", "name": "TECNOLOGIA EN REGENCIA DE FARMACIA"},
    {"code": "149", "name": "ADMINISTRACION FINANCIERA"},
    {"code": "150", "name": "ARQUITECTURA"},
    {"code": "161", "name": "INGENIERIA BIOTECNOLOGICA"},
    {"code": "162", "name": "INGENIERIA AGRONOMICA"},
    {"code": "163", "name": "INGENIERIA PECUARIA"},
    {"code": "164", "name": "INGENIERIA AGROINDUSTRIAL"},
    {"code": "165", "name": "INGENIERIA AMBIENTAL"},
    {"code": "168", "name": "ZOOTECNIA"},
    {"code": "170", "name": "LICENCIATURA EN EDUCACION INFANTIL"},
    {"code": "180", "name": "ENFERMERIA"},
    {"code": "181", "name": "SEGURIDAD Y SALUD EN EL TRABAJO"},
    {"code": "186", "name": "TEC. PROF. EN PROD. DE CERAMICA ARTESANAL - ART"},
    {"code": "187", "name": "TEC. PROF.EN FAB.INDUSTR. PRODUCTOS CER - ART"},
    {"code": "188", "name": "TEC. PROF. EN MAN. DE CALZ. Y MARROQUINERIA - ART"},
    {"code": "189", "name": "TEC. PROFESIONAL EN PROD. INDUSTRIAL-ARTICULACION"},
    {"code": "190", "name": "TECNICO PROFESIONAL EN PRODUCCION INDUSTRIAL"},
    {"code": "192", "name": "TECNOLOGIA EN OBRAS CIVILES"},
    {"code": "193", "name": "TECNOLOGIA QUIMICA"},
    {"code": "195", "name": "QUIMICA INDUSTRIAL"},
    {"code": "198", "name": "TECNOLOGIA EN PROCESOS INDUSTRIALES"},
    {"code": "211", "name": "INGENIERIA CIVIL"},
    {"code": "226", "name": "MAESTRIA EN GERENCIA DE EMPRESAS"},
    {"code": "234", "name": "TRABAJO SOCIAL"},
    {"code": "237", "name": "DOCTORADO EN EDUCACION"},
    {"code": "239", "name": "MAESTRIA EN EDUCACION MATEMATICA"},
    {"code": "240", "name": "MAESTRIA EN CIENCIAS BIOLOGICAS"},
    {"code": "242", "name": "TECNOLOGIA EN CONSTRUCCIONES CIVILES"},
    {"code": "245", "name": "MAESTRIA EN INGENIERIA DE RECURSOS HIDRAULICOS"},
    {"code": "246", "name": "MAESTRIA EN ESTUDIOS SOCIALES Y EDUCACION PARA LA PAZ"},
]


def seed_programs() -> None:
    db = SessionLocal()
    created = 0
    skipped = 0

    try:
        existing_codes = {
            code
            for (code,) in db.query(ProgramModel.code).filter(
                ProgramModel.code.in_([data["code"] for data in DEFAULT_PROGRAMS])
            )
        }

        for data in DEFAULT_PROGRAMS:
            if data["code"] in existing_codes:
                print(f"  Skipped (already exists): {data['code']} {data['name']}")
                skipped += 1
                continue

            db.add(
                ProgramModel(
                    code=data["code"],
                    name=data["name"],
                    active=True,
                )
            )
            print(f"  Created: {data['code']} {data['name']}")
            created += 1

        db.commit()
        print(
            f"Seeding complete: {created} created, {skipped} already present "
            f"({len(DEFAULT_PROGRAMS)} programs in total)."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_programs()
