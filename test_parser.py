"""Script temporal para probar el parser del PDF."""

import json
import sys
from decimal import Decimal

from api.utils.pdf_parser import parse_pdf


def default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


if len(sys.argv) < 2:
    print("Uso: python test_parser.py <ruta_al_pdf>")
    sys.exit(1)

with open(sys.argv[1], "rb") as f:
    file_bytes = f.read()

result = parse_pdf(file_bytes)

print(f"Período:      {result['period_code']}")
print(f"Departamento: {result['department_code']} - {result['department_name']}")
print(f"Docentes:     {len(result['teachers'])}")
print()

for teacher in result["teachers"]:
    avg = teacher.get("overall_average")
    print(f"[{teacher['code']}] {teacher['name']} ({teacher['contract_type']}) — promedio: {avg}")
    for g in teacher.get("groups", []):
        print(f"  {g['course_code']} {g['group']}{g['section']} {g['course_name']}")
        print(f"    enc={g['respondent_count']}  avg={g['overall_average']}")
        print(f"    comentarios: {len(g['comments'])}")

print()
print("--- JSON completo ---")
print(json.dumps(result, indent=2, default=default, ensure_ascii=False))
