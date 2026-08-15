"""
Question catalog for UFPS teacher evaluation form.
Static data — source of truth for question codes, texts, and dimensions.
"""

QUESTIONS = [
    # Desarrollo del Conocimiento
    {"code": "001", "text": "Da a conocer la programación al inicio del semestre.", "dimension": "Desarrollo del Conocimiento"},
    {"code": "002", "text": "Demuestra dominio de los temas tratados.", "dimension": "Desarrollo del Conocimiento"},
    {"code": "003", "text": "Da respuestas satisfactorias a las preguntas.", "dimension": "Desarrollo del Conocimiento"},
    {"code": "004", "text": "Relaciona situaciones problemáticas de la vida real.", "dimension": "Desarrollo del Conocimiento"},
    {"code": "005", "text": "Tiene facilidad para expresar sus ideas.", "dimension": "Desarrollo del Conocimiento"},
    {"code": "006", "text": "Genera interés por la investigación.", "dimension": "Desarrollo del Conocimiento"},
    # Desempeño Docente
    {"code": "007", "text": "Planea las actividades académicas a desarrollar.", "dimension": "Desempeño Docente"},
    {"code": "008", "text": "Fomenta la participación en clase.", "dimension": "Desempeño Docente"},
    {"code": "009", "text": "Aplica metodologías de acuerdo con las necesidades del contenido del curso.", "dimension": "Desempeño Docente"},
    {"code": "010", "text": "Es ordenado en la presentación de la clase.", "dimension": "Desempeño Docente"},
    {"code": "011", "text": "Asiste puntualmente a clase.", "dimension": "Desempeño Docente"},
    {"code": "012", "text": "Realiza actividades de asesoría.", "dimension": "Desempeño Docente"},
    {"code": "013", "text": "Aporta información bibliográfica con relación a la temática.", "dimension": "Desempeño Docente"},
    {"code": "014", "text": "Despierta motivación en su clase.", "dimension": "Desempeño Docente"},
    # Procesos de Evaluación
    {"code": "015", "text": "Los temas de evaluación concuerdan con el contenido del curso.", "dimension": "Procesos de Evaluación"},
    {"code": "016", "text": "Establece criterios de evaluación.", "dimension": "Procesos de Evaluación"},
    {"code": "017", "text": "Da a conocer el resultado de las evaluaciones oportunamente.", "dimension": "Procesos de Evaluación"},
    {"code": "018", "text": "Planea la reflexión sobre los resultados académicos del estudiante.", "dimension": "Procesos de Evaluación"},
    # Integración Interpersonal
    {"code": "019", "text": "Se muestra abierto al diálogo.", "dimension": "Integración Interpersonal"},
    {"code": "020", "text": "Su actitud refleja identidad institucional.", "dimension": "Integración Interpersonal"},
    {"code": "021", "text": "Establece relaciones de respeto con los estudiantes.", "dimension": "Integración Interpersonal"},
    {"code": "022", "text": "Considera los problemas sociales del estudiante.", "dimension": "Integración Interpersonal"},
]

DIMENSION_MAP = {
    "Desarrollo del Conocimiento": ["001", "002", "003", "004", "005", "006"],
    "Desempeño Docente": ["007", "008", "009", "010", "011", "012", "013", "014"],
    "Procesos de Evaluación": ["015", "016", "017", "018"],
    "Integración Interpersonal": ["019", "020", "021", "022"],
}

QUESTION_TEXT: dict[str, str] = {q["code"]: q["text"] for q in QUESTIONS}

QUESTION_DIMENSION: dict[str, str] = {q["code"]: q["dimension"] for q in QUESTIONS}

# The five "aspectos en seguimiento" of the official UFPS forms (Formato 2 "Ficha
# de acuerdo de mejoramiento" and Formato 3 "Plan seguimiento y mejoramiento").
# Aspects 1-4 are the evaluation dimensions above; aspect 5 has no quantitative
# indicator — it is justified with the students' written comments instead.
ASPECTS = [
    {"aspect": 1, "label": "Desarrollo de Conocimiento", "dimension": "Desarrollo del Conocimiento"},
    {"aspect": 2, "label": "Desempeño Docente", "dimension": "Desempeño Docente"},
    {"aspect": 3, "label": "Procesos de Evaluación", "dimension": "Procesos de Evaluación"},
    {"aspect": 4, "label": "Integración Interpersonal", "dimension": "Integración Interpersonal"},
    {"aspect": 5, "label": "Observaciones de los Estudiantes", "dimension": None},
]

STUDENT_COMMENTS_ASPECT = 5

ASPECT_NUMBERS: list[int] = [a["aspect"] for a in ASPECTS]

ASPECT_LABEL: dict[int, str] = {a["aspect"]: a["label"] for a in ASPECTS}

DIMENSION_ASPECT: dict[str, int] = {
    a["dimension"]: a["aspect"] for a in ASPECTS if a["dimension"]
}

ASPECT_DIMENSION: dict[int, str | None] = {
    a["aspect"]: a["dimension"] for a in ASPECTS
}


def aspect_for_target(target_type: str, target_ref: str | None) -> int | None:
    """Resolve which official form aspect (1-5) an item belongs to.

    DIMENSION items map through their dimension name, QUESTION items through the
    dimension owning the question code. Everything else (overall average,
    qualitative, pedagogical category) has no aspect and is left unassigned so the
    director can place it manually.
    """

    if target_type == "DIMENSION" and target_ref:
        return DIMENSION_ASPECT.get(target_ref)

    if target_type == "QUESTION" and target_ref:
        dimension = QUESTION_DIMENSION.get(target_ref)
        return DIMENSION_ASPECT.get(dimension) if dimension else None

    return None
