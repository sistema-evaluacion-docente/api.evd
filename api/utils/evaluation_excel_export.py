"""
Excel export for a department evaluation summary report.
"""

import io

import openpyxl
from fastapi.responses import StreamingResponse

from api.utils.excel_styles import EXCEL_MIME


def build_evaluation_report(summary: dict) -> tuple[io.BytesIO, str]:
    """Build the department evaluation summary Excel workbook.

    Returns (buffer, filename).
    """

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumen Evaluación Docente"

    ws.append(
        [
            "Ranking",
            "Nombre",
            "Código",
            "Tipo Contrato",
            "Grupos Evaluados",
            "Promedio",
        ]
    )

    for item in summary["ranking"]:
        ws.append(
            [
                item["rank"],
                item["name"] or "",
                item["institutional_code"],
                item["contract_type"] or "",
                item["group_count"],
                item["overall_average"],
            ]
        )

    ws.append([])
    ws.append(["", "Promedio Departamento", "", "", "", summary["department_average"]])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"evaluacion_{summary['period_code']}_{summary['evaluation_id']}.xlsx"

    return buffer, filename


def evaluation_streaming_response(
    buffer: io.BytesIO, filename: str
) -> StreamingResponse:
    """Return a StreamingResponse for the Excel file."""

    return StreamingResponse(
        buffer,
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
