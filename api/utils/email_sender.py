"""
Transport for outgoing mail.

Pure "message in, message out" module — the copy and the templates live in
``api/utils/plan_email.py``, and the decision of *when* to send belongs to the
services. Same shape as ``api/utils/improvement_plan_pdf.py``.

Two backends behind one interface. ``smtp`` sends through any SMTP server: a
personal Gmail account with an app password while the system is being tried out,
the institutional mailbox once its credentials are handed over — same code, a
different ``.env``. ``console`` only logs the rendered message, so the app and
the whole test suite run without credentials of any kind.
"""

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr
from functools import lru_cache
from typing import Protocol

from api.config import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InlineImage:
    """An image the HTML body refers to as ``src="cid:<cid>"``.

    Mail clients need the bytes to travel with the message: Gmail and most
    webmail strip ``data:`` URIs, so the letterhead cannot simply be inlined the
    way the Word copy of the official forms does it.
    """

    cid: str
    filename: str
    content: bytes
    subtype: str = "png"


@dataclass(frozen=True)
class OutgoingEmail:
    """One message, already rendered."""

    to: str
    subject: str
    html: str
    text: str
    inline_images: tuple[InlineImage, ...] = field(default_factory=tuple)


class EmailBackend(Protocol):
    """How a message reaches the outside world."""

    def send(self, email: OutgoingEmail) -> None:
        """Deliver the message, raising if it cannot be delivered."""


def build_message(email: OutgoingEmail, sender: str, sender_name: str) -> EmailMessage:
    """Assemble the MIME message both backends work with.

    The plain-text part is set first and the HTML added as an alternative, which
    is the order that makes clients prefer the HTML while leaving something
    readable for those that refuse it. The images then attach to the HTML part,
    producing the ``multipart/related`` that resolves the ``cid:`` references.
    """

    message = EmailMessage()

    message["Subject"] = email.subject
    message["From"] = formataddr((sender_name, sender))
    message["To"] = email.to

    message.set_content(email.text)
    message.add_alternative(email.html, subtype="html")

    html_part = message.get_payload()[-1]

    for image in email.inline_images:
        html_part.add_related(
            image.content,
            maintype="image",
            subtype=image.subtype,
            cid=f"<{image.cid}>",
            filename=image.filename,
        )

    return message


class SmtpBackend:
    """Sends through an SMTP server."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        sender_name: str,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender or user
        self.sender_name = sender_name
        self.use_tls = use_tls

    def send(self, email: OutgoingEmail) -> None:
        message = build_message(email, self.sender, self.sender_name)

        # Port 465 speaks SSL from the first byte; 587 opens in the clear and is
        # upgraded with STARTTLS. Getting this backwards hangs the connection
        # rather than failing outright, hence the explicit split.
        if self.use_tls:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls(context=ssl.create_default_context())
                self._deliver(server, message)
        else:
            with smtplib.SMTP_SSL(
                self.host, self.port, context=ssl.create_default_context()
            ) as server:
                self._deliver(server, message)

        logger.info("Correo enviado a %s: %s", email.to, email.subject)

    def _deliver(self, server: smtplib.SMTP, message: EmailMessage) -> None:
        if self.user:
            server.login(self.user, self.password)

        server.send_message(message)


class ConsoleBackend:
    """Writes the message to the log instead of sending it.

    The default, so a fresh checkout runs without credentials and nobody emails
    a real teacher by accident while trying the system out.
    """

    def send(self, email: OutgoingEmail) -> None:
        logger.info(
            "[correo:console] Para: %s | Asunto: %s\n%s",
            email.to,
            email.subject,
            email.text,
        )


@lru_cache(maxsize=1)
def get_backend() -> EmailBackend:
    """The backend this deployment is configured with."""

    if config.MAIL_BACKEND == "smtp":
        return SmtpBackend(
            host=config.SMTP_HOST,
            port=config.SMTP_PORT,
            user=config.SMTP_USER,
            password=config.SMTP_PASSWORD,
            sender=config.MAIL_FROM,
            sender_name=config.MAIL_FROM_NAME,
            use_tls=config.SMTP_USE_TLS,
        )

    return ConsoleBackend()


def send_email(email: OutgoingEmail) -> None:
    """Send one message through the configured backend.

    Blocking: callers on the event loop must hand it to ``asyncio.to_thread``.
    """

    if not config.MAIL_ENABLED:
        logger.info("Correo desactivado; no se envía a %s", email.to)
        return

    get_backend().send(email)
