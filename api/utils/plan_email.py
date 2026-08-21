"""
The messages the improvement-plan module sends.

Pure "context in, message out" module: it renders, it does not decide when to
send nor how the message travels — that is ``api/utils/email_sender.py`` and the
services. Same split as ``api/utils/improvement_plan_pdf.py``.
"""

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api.utils.email_sender import InlineImage, OutgoingEmail
from api.utils.plan_links import absolute, teacher_plan_path

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
        director_name=director_name,
        director_title=director_title(department_name),
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
