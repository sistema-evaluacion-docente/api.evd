"""
The messages the improvement-plan module sends.

Pure "context in, message out" module: it renders, it does not decide when to
send nor how the message travels — that is ``api/utils/email_sender.py`` and the
services. Same split as ``api/utils/improvement_plan_pdf.py``.
"""

import datetime
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api.utils.email_sender import InlineImage, OutgoingEmail
from api.utils.plan_links import absolute, manager_plan_path, teacher_plan_path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "emails"
ASSETS_DIR = TEMPLATES_DIR / "assets"

# The letterhead, and the id the templates refer to it by. The institutional
# mark rather than a department one: the same message goes out on behalf of
# every department, so nothing here may name a single one.
HEADER_FILENAME = "logo-ufps.png"
HEADER_CID = "logo-ufps"


@lru_cache(maxsize=1)
def _header_image() -> InlineImage:
    """The letterhead, read once and reused for every message."""

    return InlineImage(
        cid=HEADER_CID,
        filename=HEADER_FILENAME,
        content=(ASSETS_DIR / HEADER_FILENAME).read_bytes(),
    )


@lru_cache(maxsize=1)
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def director_title(department_name: str | None) -> str:
    """How the director signs off, given whatever the department is called.

    Departments are stored with the word already in the name ("Departamento de
    Sistemas e Informática"), but not all of them have to be — so the word is
    added only when it is missing, instead of printing "Director Departamento
    Departamento de ...".
    """

    name = (department_name or "").strip()

    if not name:
        return "Director de Departamento"

    if name.lower().startswith("departamento"):
        return f"Director {name}"

    return f"Director Departamento {name}"


def plan_url(plan_id: int) -> str:
    """Absolute link to the teacher's own view of a plan."""

    return absolute(teacher_plan_path(plan_id))


def manager_plan_url(plan_id: int) -> str:
    """Absolute link to the screen the plan is managed from."""

    return absolute(manager_plan_path(plan_id))


# The two sides the evidence loop writes to, and how each is addressed and
# signed. A teacher hears from the department head, because that is who asked;
# a director hears from the platform, because the teacher did not write to them.
PLATFORM_SIGNER = "Sistema de Evaluación Docente"
PLATFORM_SIGNER_TITLE = "Universidad Francisco de Paula Santander"


def render_plan_created(
    *,
    plan_id: int,
    plan_title: str,
    teacher_name: str,
    teacher_email: str,
    director_name: str,
    department_name: str | None,
    period_code: str | None = None,
) -> OutgoingEmail:
    """The message a teacher gets when a plan is drawn up for them."""

    url = plan_url(plan_id)
    subject = f"Plan de mejoramiento registrado a su nombre: {plan_title}"

    html = _environment().get_template("plan_created.html").render(
        subject=subject,
        header_cid=HEADER_CID,
        teacher_name=teacher_name,
        plan_title=plan_title,
        period_code=period_code,
        plan_url=url,
        signer_name=director_name,
        signer_title=director_title(department_name),
    )

    return OutgoingEmail(
        to=teacher_email,
        subject=subject,
        html=html,
        text=_plan_created_text(
            teacher_name=teacher_name,
            plan_title=plan_title,
            period_code=period_code,
            url=url,
            director_name=director_name,
            director_title=director_title(department_name),
        ),
        inline_images=(_header_image(),),
    )


def _plan_created_text(
    *,
    teacher_name: str,
    plan_title: str,
    period_code: str | None,
    url: str,
    director_name: str,
    director_title: str,
) -> str:
    """Plain-text twin of the message, for clients that refuse HTML."""

    period = f" del periodo {period_code}" if period_code else ""

    return f"""Estimado(a) profesor(a) {teacher_name},

A partir de los resultados de la evaluación docente{period}, se ha registrado un
plan de mejoramiento a su nombre: «{plan_title}».

El plan recoge los compromisos acordados y el seguimiento que se hará durante el
semestre. Puede consultarlo en el Sistema de Evaluación Docente en el siguiente
enlace:

{url}

Cualquier inquietud puede dirigirla a la dirección del departamento.

Cordialmente,

{director_name}
{director_title}
Cúcuta,CO

--
Avenida Gran Colombia No. 12E-96 Barrio Colsag, San José de Cúcuta - Colombia.
Teléfono (057)(7) 5776655
"""


# How each verdict reads to the teacher, and what the message says after it.
# The enum carries three values (the two the director picks plus the manual
# close an admin can force), and a plan settled either way still deserves a
# sentence that does not read as boilerplate.
_CLOSE_RESULT_LABEL = {
    "CUMPLIDO": "Cumplido",
    "NO_CUMPLIDO": "No cumplido"
}

_CLOSE_RESULT_NOTE = {
    "CUMPLIDO": (
        "Agradecemos su compromiso con el proceso. El cumplimiento se verificará con "
        "los resultados de la evaluación docente del siguiente periodo."
    ),
    "NO_CUMPLIDO": (
        "Quedaron compromisos sin alcanzar. La dirección del departamento le indicará "
        "los pasos a seguir."
    )
}


def close_result_label(result: str) -> str:
    """How a close verdict is written out for a person to read."""

    return _CLOSE_RESULT_LABEL.get(result, "Cerrado")


def render_plan_closed(
    *,
    plan_id: int,
    plan_title: str,
    teacher_name: str,
    teacher_email: str,
    director_name: str,
    department_name: str | None,
    result: str,
    reason: str | None = None,
    period_code: str | None = None,
) -> OutgoingEmail:
    """The message a teacher gets when their plan is settled and closed."""

    url = plan_url(plan_id)
    label = close_result_label(result)
    note = _CLOSE_RESULT_NOTE.get(result, _CLOSE_RESULT_NOTE["MANUAL"])
    subject = f"Cierre de su plan de mejoramiento: {plan_title}"

    html = _environment().get_template("plan_closed.html").render(
        subject=subject,
        header_cid=HEADER_CID,
        teacher_name=teacher_name,
        plan_title=plan_title,
        period_code=period_code,
        result_label=label,
        reason=reason,
        closing_note=note,
        plan_url=url,
        signer_name=director_name,
        signer_title=director_title(department_name),
    )

    return OutgoingEmail(
        to=teacher_email,
        subject=subject,
        html=html,
        text=_plan_closed_text(
            teacher_name=teacher_name,
            plan_title=plan_title,
            period_code=period_code,
            result_label=label,
            reason=reason,
            closing_note=note,
            url=url,
            director_name=director_name,
            director_title=director_title(department_name),
        ),
        inline_images=(_header_image(),),
    )


def _plan_closed_text(
    *,
    teacher_name: str,
    plan_title: str,
    period_code: str | None,
    result_label: str,
    reason: str | None,
    closing_note: str,
    url: str,
    director_name: str,
    director_title: str,
) -> str:
    """Plain-text twin of the message, for clients that refuse HTML."""

    period = f", originado en la evaluación docente del periodo {period_code}," if period_code else ""
    observations = f"\nObservaciones: {reason}\n" if reason else ""

    return f"""Estimado(a) profesor(a) {teacher_name},

Le informamos que su plan de mejoramiento «{plan_title}»{period} ha sido cerrado
por la dirección del departamento.

Resultado del cierre: {result_label}
{observations}
{closing_note}

Puede consultar el plan cerrado, con sus compromisos y seguimientos, en el
Sistema de Evaluación Docente:

{url}

Cualquier inquietud puede dirigirla a la dirección del departamento.

Cordialmente,

{director_name}
{director_title}
Cúcuta,CO

--
Avenida Gran Colombia No. 12E-96 Barrio Colsag, San José de Cúcuta - Colombia.
Teléfono (057)(7) 5776655
"""


# --------------------------------------------------------------------------- #
# The evidence loop                                                            #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _EvidenceEvent:
    """One message of the loop, before it is laid out.

    The five of them differ only in these fields — everything else is the
    letterhead, the link and the footer — so they share one template and one
    plain-text twin instead of a copy of each per event.
    """

    to: str
    subject: str
    greeting: str
    body: str
    cta: str
    url: str
    signer_name: str
    signer_title: str
    detail: str | None = None
    detail_label: str | None = None


def _render_evidence_event(event: _EvidenceEvent) -> OutgoingEmail:
    """Lays one event out as the message that actually goes."""

    html = (
        _environment()
        .get_template("evidence_event.html")
        .render(
            subject=event.subject,
            header_cid=HEADER_CID,
            greeting=event.greeting,
            body=event.body,
            detail=event.detail,
            detail_label=event.detail_label,
            cta=event.cta,
            plan_url=event.url,
            signer_name=event.signer_name,
            signer_title=event.signer_title,
        )
    )

    return OutgoingEmail(
        to=event.to,
        subject=event.subject,
        html=html,
        text=_evidence_event_text(event),
        inline_images=(_header_image(),),
    )


def _evidence_event_text(event: _EvidenceEvent) -> str:
    """Plain-text twin, for clients that refuse HTML."""

    detail = ""

    if event.detail:
        label = f"{event.detail_label}:\n" if event.detail_label else ""
        detail = f"\n{label}{event.detail}\n"

    return f"""{event.greeting},

{event.body}
{detail}
{event.cta}

{event.url}

Cualquier inquietud puede dirigirla a la dirección del departamento.

Cordialmente,

{event.signer_name}
{event.signer_title}
Cúcuta,CO

--
Avenida Gran Colombia No. 12E-96 Barrio Colsag, San José de Cúcuta - Colombia.
Teléfono (057)(7) 5776655
"""


def _teacher_greeting(name: str) -> str:
    return f"Estimado(a) profesor(a) {name}"


def _director_greeting(name: str) -> str:
    return f"Estimado(a) director(a) {name}"


def _due(due_date: datetime.date | None) -> str:
    """The deadline, said in the middle of a sentence, or nothing at all."""

    if not due_date:
        return ""

    return f", con fecha límite del {due_date.strftime('%d/%m/%Y')}"


def render_evidence_requested(
    *,
    plan_id: int,
    plan_title: str,
    request_title: str,
    request_description: str | None,
    due_date: datetime.date | None,
    teacher_name: str,
    teacher_email: str,
    director_name: str,
    department_name: str | None,
) -> OutgoingEmail:
    """The message a teacher gets when a deliverable is asked of them."""

    detail = request_title

    if request_description:
        detail = f"{request_title} — {request_description}"

    return _render_evidence_event(
        _EvidenceEvent(
            to=teacher_email,
            subject=f"Evidencia solicitada en su plan de mejoramiento: {plan_title}",
            greeting=_teacher_greeting(teacher_name),
            body=(
                f"En el seguimiento de su plan de mejoramiento «{plan_title}» se le "
                f"ha solicitado un nuevo entregable{_due(due_date)}."
            ),
            detail_label="Entregable solicitado",
            detail=detail,
            cta=(
                "Puede adjuntarlo en el Sistema de Evaluación Docente en el "
                "siguiente enlace:"
            ),
            url=plan_url(plan_id),
            signer_name=director_name,
            signer_title=director_title(department_name),
        )
    )


def render_evidence_reviewed(
    *,
    plan_id: int,
    plan_title: str,
    approved: bool,
    comment: str | None,
    teacher_name: str,
    teacher_email: str,
    director_name: str,
    department_name: str | None,
) -> OutgoingEmail:
    """The message a teacher gets once their evidence has been looked at."""

    verdict = "aprobada" if approved else "devuelta"
    body = (
        f"La evidencia que adjuntó a su plan de mejoramiento «{plan_title}» fue "
        f"revisada y {verdict}."
    )

    if not approved:
        body += " Debe enviar una nueva."

    return _render_evidence_event(
        _EvidenceEvent(
            to=teacher_email,
            subject=(
                f"Evidencia {'aprobada' if approved else 'rechazada'} en su plan "
                f"de mejoramiento: {plan_title}"
            ),
            greeting=_teacher_greeting(teacher_name),
            body=body,
            detail_label="Observación del director" if comment else None,
            detail=comment,
            cta="Puede consultar el detalle en el siguiente enlace:",
            url=plan_url(plan_id),
            signer_name=director_name,
            signer_title=director_title(department_name),
        )
    )


def render_evidence_comment_for_teacher(
    *,
    plan_id: int,
    plan_title: str,
    comment: str,
    teacher_name: str,
    teacher_email: str,
    director_name: str,
    department_name: str | None,
) -> OutgoingEmail:
    """A comment the director left on the teacher's evidence thread."""

    return _render_evidence_event(
        _EvidenceEvent(
            to=teacher_email,
            subject=f"Nuevo comentario en su plan de mejoramiento: {plan_title}",
            greeting=_teacher_greeting(teacher_name),
            body=(
                "La dirección del departamento dejó un comentario en el "
                f"seguimiento de su plan de mejoramiento «{plan_title}»."
            ),
            detail_label="Comentario",
            detail=comment,
            cta="Puede responderlo en el siguiente enlace:",
            url=plan_url(plan_id),
            signer_name=director_name,
            signer_title=director_title(department_name),
        )
    )


def render_evidence_comment_for_director(
    *,
    plan_id: int,
    plan_title: str,
    comment: str,
    teacher_name: str,
    director_name: str,
    director_email: str,
) -> OutgoingEmail:
    """A comment the teacher left, on its way to whoever follows the plan up."""

    return _render_evidence_event(
        _EvidenceEvent(
            to=director_email,
            subject=f"{teacher_name} comentó en un plan de mejoramiento",
            greeting=_director_greeting(director_name),
            body=(
                f"El(la) profesor(a) {teacher_name} dejó un comentario en el "
                f"seguimiento del plan de mejoramiento «{plan_title}»."
            ),
            detail_label="Comentario",
            detail=comment,
            cta="Puede consultarlo y responderlo en el siguiente enlace:",
            url=manager_plan_url(plan_id),
            signer_name=PLATFORM_SIGNER,
            signer_title=PLATFORM_SIGNER_TITLE,
        )
    )


def render_evidence_submitted(
    *,
    plan_id: int,
    plan_title: str,
    teacher_name: str,
    director_name: str,
    director_email: str,
) -> OutgoingEmail:
    """The notice that a teacher has something waiting to be reviewed."""

    return _render_evidence_event(
        _EvidenceEvent(
            to=director_email,
            subject=f"{teacher_name} adjuntó una evidencia a su plan de mejoramiento",
            greeting=_director_greeting(director_name),
            body=(
                f"El(la) profesor(a) {teacher_name} adjuntó una evidencia al plan "
                f"de mejoramiento «{plan_title}». Queda pendiente de su revisión."
            ),
            cta="Puede revisarla en el siguiente enlace:",
            url=manager_plan_url(plan_id),
            signer_name=PLATFORM_SIGNER,
            signer_title=PLATFORM_SIGNER_TITLE,
        )
    )


def render_document_signed(
    *,
    plan_id: int,
    plan_title: str,
    format_name: str,
    format_label: str,
    teacher_name: str,
    teacher_email: str,
    director_name: str,
    department_name: str | None,
) -> OutgoingEmail:
    """The message a teacher gets once a form of their plan carries signatures.

    The signed scan is what the plan actually *is* — the generated PDF is only
    the draft it was printed from — so the teacher is told the moment there is
    one to read, instead of finding out the next time they happen to open the
    page.
    """

    return _render_evidence_event(
        _EvidenceEvent(
            to=teacher_email,
            subject=f"{format_name} firmado de su plan de mejoramiento: {plan_title}",
            greeting=_teacher_greeting(teacher_name),
            body=(
                f"Se adjuntó a su plan de mejoramiento «{plan_title}» el "
                f"{format_name} ({format_label}) con las firmas correspondientes."
            ),
            cta="Puede consultarlo y descargarlo en el siguiente enlace:",
            url=plan_url(plan_id),
            signer_name=director_name,
            signer_title=director_title(department_name),
        )
    )
