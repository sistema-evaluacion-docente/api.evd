"""
Template-based improvement action suggestions.

Deterministic catalogue that maps each evaluation dimension (and a generic
fallback) to a list of suggested improvement actions. Consumed by the
``/improvement-plans/at-risk`` endpoint to pre-fill a plan when a teacher
scores below the institutional threshold.

The public entry point ``suggest_actions(target_type, target_ref)`` has a
stable signature so the underlying catalogue can later be replaced by a real
ML/LLM component without touching the callers.
"""

# Keyed by the exact dimension names in api/utils/dimensions.py DIMENSION_MAP
DIMENSION_SUGGESTIONS: dict[str, list[str]] = {
    "Desarrollo del Conocimiento": [
        "Entregar y socializar la programación del curso en la primera semana.",
        "Preparar ejemplos aplicados a problemas reales para cada tema.",
        "Realizar sesiones de refuerzo sobre los temas con menor comprensión.",
        "Incorporar referencias bibliográficas actualizadas por unidad.",
    ],
    "Desempeño Docente": [
        "Planear cada clase con objetivos y actividades explícitas.",
        "Registrar y cumplir la puntualidad y asistencia a clase.",
        "Diversificar metodologías activas según el contenido del curso.",
        "Definir y difundir horarios de asesoría a los estudiantes.",
    ],
    "Procesos de Evaluación": [
        "Publicar los criterios y rúbricas de evaluación al inicio del curso.",
        "Alinear los temas evaluados con el contenido efectivamente visto.",
        "Entregar resultados de las evaluaciones dentro del plazo institucional.",
        "Realizar retroalimentación de los resultados con el grupo.",
    ],
    "Integración Interpersonal": [
        "Fomentar espacios de diálogo y participación respetuosa en clase.",
        "Atender de forma oportuna las inquietudes de los estudiantes.",
        "Aplicar acuerdos de convivencia y respeto en el aula.",
        "Considerar la situación particular de los estudiantes en el proceso.",
    ],
}

GENERIC_SUGGESTIONS: list[str] = [
    "Elevar el promedio general de evaluación por encima del umbral institucional.",
    "Acordar acciones concretas de mejora y hacerles seguimiento en el semestre.",
    "Documentar evidencias del avance (planes de clase, asistencia, materiales).",
]


def suggest_actions(target_type: str, target_ref: str | None = None) -> list[str]:
    """Return suggested improvement actions for a given target.

    Args:
        target_type: DIMENSION / PEDAGOGICAL_CATEGORY / OVERALL_AVERAGE / QUALITATIVE.
        target_ref: dimension name (for DIMENSION) or category id (for category).

    Returns:
        A list of suggested action strings (never empty).
    """

    if target_type == "DIMENSION" and target_ref:
        return DIMENSION_SUGGESTIONS.get(target_ref, GENERIC_SUGGESTIONS)

    return GENERIC_SUGGESTIONS
