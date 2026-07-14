"""
Template-based improvement action suggestions.

Deterministic catalogue that maps each evaluation dimension, each question of
the evaluation form (and a generic fallback) to a list of suggested improvement
actions. Consumed by the ``/improvement-plans`` endpoints to pre-fill a plan
with the indicator the director wants the teacher to improve.

The public entry point ``suggest_actions(target_type, target_ref)`` has a
stable signature so the underlying catalogue can later be replaced by a real
ML/LLM component without touching the callers.
"""

from api.utils.dimensions import DIMENSION_MAP, QUESTION_DIMENSION, QUESTION_TEXT

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

# Keyed by the question codes in api/utils/dimensions.py QUESTIONS
QUESTION_SUGGESTIONS: dict[str, list[str]] = {
    "001": [
        "Entregar y socializar el programa del curso en la primera semana de clase.",
        "Publicar el cronograma de temas y evaluaciones en la plataforma del curso.",
    ],
    "002": [
        "Actualizar el material de clase con bibliografía y ejemplos recientes.",
        "Participar en actividades de formación disciplinar sobre los temas del curso.",
    ],
    "003": [
        "Reservar un espacio de preguntas al cierre de cada sesión.",
        "Preparar respuestas y ejemplos para las dudas más frecuentes del curso.",
    ],
    "004": [
        "Incluir al menos un caso o problema real por unidad temática.",
        "Diseñar talleres con escenarios del ejercicio profesional.",
    ],
    "005": [
        "Estructurar cada clase con introducción, desarrollo y síntesis final.",
        "Apoyar la explicación con material visual y ejemplos graduados.",
    ],
    "006": [
        "Proponer lecturas de artículos científicos relacionados con el curso.",
        "Vincular actividades del curso con semilleros o proyectos de investigación.",
    ],
    "007": [
        "Entregar un plan de clase por sesión con objetivos y actividades.",
        "Definir con anticipación los recursos y tiempos de cada actividad.",
    ],
    "008": [
        "Usar dinámicas de participación activa (preguntas dirigidas, trabajo en grupo).",
        "Asignar roles o exposiciones cortas a los estudiantes.",
    ],
    "009": [
        "Diversificar las metodologías según el tipo de contenido (teórico o práctico).",
        "Incorporar prácticas, laboratorios o estudios de caso en las unidades aplicadas.",
    ],
    "010": [
        "Iniciar cada sesión presentando la agenda y los objetivos de la clase.",
        "Organizar el material de apoyo en una secuencia clara y numerada.",
    ],
    "011": [
        "Cumplir el horario de inicio y cierre de todas las sesiones.",
        "Reportar y reprogramar oportunamente las clases que deban cancelarse.",
    ],
    "012": [
        "Publicar y cumplir un horario semanal de asesoría.",
        "Registrar la asistencia y los temas atendidos en las asesorías.",
    ],
    "013": [
        "Entregar bibliografía básica y complementaria por unidad temática.",
        "Compartir material de consulta accesible en la plataforma del curso.",
    ],
    "014": [
        "Relacionar los contenidos con el desempeño profesional del estudiante.",
        "Reconocer y retroalimentar los avances del grupo durante el semestre.",
    ],
    "015": [
        "Construir las evaluaciones a partir de los objetivos declarados en el programa.",
        "Revisar la correspondencia entre lo evaluado y lo efectivamente visto en clase.",
    ],
    "016": [
        "Publicar las rúbricas y criterios de calificación antes de cada evaluación.",
        "Socializar la ponderación de cada actividad al inicio del semestre.",
    ],
    "017": [
        "Entregar las calificaciones dentro del plazo institucional establecido.",
        "Publicar los resultados antes de aplicar la siguiente evaluación.",
    ],
    "018": [
        "Realizar una sesión de retroalimentación grupal después de cada corte.",
        "Acordar acciones de refuerzo con los estudiantes de bajo desempeño.",
    ],
    "019": [
        "Habilitar espacios de escucha y canales de comunicación con el grupo.",
        "Atender las inquietudes de los estudiantes de forma oportuna y respetuosa.",
    ],
    "020": [
        "Aplicar y difundir los lineamientos y valores institucionales en clase.",
        "Participar en las actividades académicas e institucionales del departamento.",
    ],
    "021": [
        "Acordar reglas de convivencia con el grupo en la primera semana.",
        "Dar un trato equitativo y respetuoso en todas las interacciones.",
    ],
    "022": [
        "Identificar y remitir a bienestar universitario los casos que lo requieran.",
        "Flexibilizar de forma justificada las actividades ante situaciones especiales.",
    ],
}

GENERIC_SUGGESTIONS: list[str] = [
    "Elevar el promedio general de evaluación por encima del umbral institucional.",
    "Acordar acciones concretas de mejora y hacerles seguimiento en el semestre.",
    "Documentar evidencias del avance (planes de clase, asistencia, materiales).",
]

OVERALL_LABEL = "Promedio general del docente"
DIMENSION_OVERALL_LABEL = "Nota general de la dimensión"


def suggest_actions(target_type: str, target_ref: str | None = None) -> list[str]:
    """Return suggested improvement actions for a given target.

    Args:
        target_type: DIMENSION / QUESTION / PEDAGOGICAL_CATEGORY /
            OVERALL_AVERAGE / QUALITATIVE.
        target_ref: dimension name (DIMENSION), question code (QUESTION) or
            category id (PEDAGOGICAL_CATEGORY).

    Returns:
        A list of suggested action strings (never empty).
    """

    if target_type == "DIMENSION" and target_ref:
        return DIMENSION_SUGGESTIONS.get(target_ref, GENERIC_SUGGESTIONS)

    if target_type == "QUESTION" and target_ref:
        actions = QUESTION_SUGGESTIONS.get(target_ref)
        if actions:
            return actions
        dimension = QUESTION_DIMENSION.get(target_ref)
        return DIMENSION_SUGGESTIONS.get(dimension, GENERIC_SUGGESTIONS)

    return GENERIC_SUGGESTIONS


def build_indicator_catalog() -> dict:
    """Selectable indicators for a plan item (compromiso).

    Each dimension exposes its own overall score plus every question of the
    evaluation form that belongs to it, so a director can commit either to the
    dimension as a whole or to one specific question.
    """

    return {
        "overall": {
            "target_type": "OVERALL_AVERAGE",
            "target_ref": None,
            "label": OVERALL_LABEL,
            "suggestions": suggest_actions("OVERALL_AVERAGE"),
        },
        "dimensions": [
            {
                "dimension": dimension,
                "target_type": "DIMENSION",
                "target_ref": dimension,
                "label": DIMENSION_OVERALL_LABEL,
                "suggestions": suggest_actions("DIMENSION", dimension),
                "questions": [
                    {
                        "target_type": "QUESTION",
                        "target_ref": code,
                        "code": code,
                        "text": QUESTION_TEXT.get(code, code),
                        "suggestions": suggest_actions("QUESTION", code),
                    }
                    for code in codes
                ],
            }
            for dimension, codes in DIMENSION_MAP.items()
        ],
    }
