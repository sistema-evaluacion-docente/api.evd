"""
Teaching modality of a course group.

UFPS evaluates the same instrument in two kinds of programs and publishes one
PDF per kind: the title line of every page reads 'Programas Presenciales' or
'Programas a Distancia'. That title is the only place the modality appears, so
it travels from there down to every academic group the document creates.
"""

from api.exceptions import ValidationError

PRESENCIAL = "PRESENCIAL"
DISTANCIA = "DISTANCIA"

MODALITIES = (PRESENCIAL, DISTANCIA)

# Nombres de cara al usuario, para mensajes de error y auditoría.
MODALITY_LABELS = {PRESENCIAL: "presencial", DISTANCIA: "a distancia"}


def normalize_modality(value: str | None) -> str | None:
    """Return the canonical modality for a raw value, or None if unknown."""

    if not value:
        return None

    candidate = value.strip().upper()

    return candidate if candidate in MODALITIES else None


def modality_label(value: str | None) -> str:
    """Return the Spanish name of a modality, for user-facing messages."""

    return MODALITY_LABELS.get(normalize_modality(value) or "", "sin modalidad")


def validated_modality(value: str | None) -> str | None:
    """Return the canonical modality, rejecting values outside the catalog.

    Endpoints declare the modality as a Literal, so FastAPI already refuses a
    bad one; this guards the services against every other caller."""

    if value is None:
        return None

    normalized = normalize_modality(value)

    if normalized is None:
        raise ValidationError(
            f"Modalidad '{value}' no válida. Use PRESENCIAL o DISTANCIA"
        )

    return normalized
