"""
When the system suggests an improvement plan for a teacher.

A single place for the rule, so the candidates endpoint, the auto-detection
list and the notification raised after an evaluation is analysed can never
disagree on who needs a plan.

It is a suggestion, never a verdict: the plan is a formal agreement born of an
acta, so the director is the one who decides.
"""

HIGH_RISK_LEVEL_NAME = "ALTO"


def is_plan_suggested(candidate: dict) -> bool:
    """Whether the results of a teacher call for an improvement plan.

    Fires on the overall average or any single indicator under the
    institutional threshold, or on a student comment the AI classified as
    high risk. A teacher can average 4.0 and still be at 2.0 in punctuality,
    so the overall average alone is not enough.
    """

    return bool(
        candidate.get("below_threshold")
        or candidate.get("weak_dimensions")
        or candidate.get("weak_questions")
        or (candidate.get("high_risk_comment_count") or 0) > 0
    )


def suggestion_reasons(candidate: dict) -> list[str]:
    """Why the plan is being suggested, ready to be read by the director."""

    reasons: list[str] = []

    if candidate.get("below_threshold"):
        reasons.append("promedio general bajo el umbral")

    weak = len(candidate.get("weak_dimensions") or []) + len(
        candidate.get("weak_questions") or []
    )

    if weak:
        reasons.append(
            f"{weak} indicador bajo el umbral"
            if weak == 1
            else f"{weak} indicadores bajo el umbral"
        )

    risky = candidate.get("high_risk_comment_count") or 0

    if risky:
        reasons.append(
            f"{risky} comentario de riesgo alto"
            if risky == 1
            else f"{risky} comentarios de riesgo alto"
        )

    return reasons
