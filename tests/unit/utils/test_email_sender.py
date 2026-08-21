"""Tests for the outgoing-mail transport."""

from unittest.mock import MagicMock, patch

import pytest

from api.utils import email_sender
from api.utils.email_sender import (
    ConsoleBackend,
    InlineImage,
    OutgoingEmail,
    SmtpBackend,
    build_message,
    get_backend,
    send_email,
)


@pytest.fixture
def email():
    return OutgoingEmail(
        to="ada@ufps.edu.co",
        subject="Plan de mejoramiento",
        html='<p>Hola</p><img src="cid:logo" />',
        text="Hola",
        inline_images=(
            InlineImage(cid="logo", filename="logo.png", content=b"\x89PNG"),
        ),
    )


@pytest.fixture(autouse=True)
def _clear_backend_cache():
    """The backend is memoised; each test picks its own configuration."""

    get_backend.cache_clear()
    yield
    get_backend.cache_clear()


class TestBuildMessage:
    """The MIME message both backends hand to the server."""

    def test_addresses_the_message(self, email):
        message = build_message(email, "dpto@ufps.edu.co", "Departamento")

        assert message["To"] == "ada@ufps.edu.co"
        assert message["Subject"] == "Plan de mejoramiento"
        assert message["From"] == "Departamento <dpto@ufps.edu.co>"

    def test_offers_text_and_html(self, email):
        """Test the plain-text part comes first so HTML is the preferred one."""

        message = build_message(email, "dpto@ufps.edu.co", "Departamento")
        types = [part.get_content_type() for part in message.walk()]

        assert "text/plain" in types
        assert "text/html" in types

    def test_carries_the_inline_image_by_content_id(self, email):
        """Test the image attaches to the HTML part, forming multipart/related."""

        message = build_message(email, "dpto@ufps.edu.co", "Departamento")
        images = [
            part for part in message.walk() if part.get_content_type() == "image/png"
        ]

        assert len(images) == 1
        assert images[0]["Content-ID"] == "<logo>"
        assert "multipart/related" in [p.get_content_type() for p in message.walk()]

    def test_sends_nothing_extra_when_there_are_no_images(self):
        message = build_message(
            OutgoingEmail(to="a@b.co", subject="s", html="<p>h</p>", text="h"),
            "dpto@ufps.edu.co",
            "Departamento",
        )

        assert not [
            part for part in message.walk() if part.get_content_type() == "image/png"
        ]


class TestConsoleBackend:
    """The default: writes to the log so nobody is emailed by accident."""

    def test_opens_no_connection(self, email):
        with patch("api.utils.email_sender.smtplib.SMTP") as smtp:
            ConsoleBackend().send(email)

        smtp.assert_not_called()


class TestSmtpBackend:
    """The real transport."""

    def test_upgrades_the_connection_with_starttls(self, email):
        with patch("api.utils.email_sender.smtplib.SMTP") as smtp:
            server = smtp.return_value.__enter__.return_value

            SmtpBackend(
                host="smtp.gmail.com",
                port=587,
                user="dpto@ufps.edu.co",
                password="clave-de-aplicacion",
                sender="dpto@ufps.edu.co",
                sender_name="Departamento",
                use_tls=True,
            ).send(email)

        smtp.assert_called_once_with("smtp.gmail.com", 587)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("dpto@ufps.edu.co", "clave-de-aplicacion")
        server.send_message.assert_called_once()

    def test_speaks_ssl_from_the_first_byte_on_465(self, email):
        """Test port 465 must not be opened in the clear and then upgraded."""

        with patch("api.utils.email_sender.smtplib.SMTP_SSL") as smtp:
            SmtpBackend(
                host="smtp.gmail.com",
                port=465,
                user="dpto@ufps.edu.co",
                password="clave",
                sender="dpto@ufps.edu.co",
                sender_name="Departamento",
                use_tls=False,
            ).send(email)

        smtp.assert_called_once()
        smtp.return_value.__enter__.return_value.send_message.assert_called_once()

    def test_skips_the_login_on_a_server_without_credentials(self, email):
        """Test an internal relay that authenticates by IP is not logged into."""

        with patch("api.utils.email_sender.smtplib.SMTP") as smtp:
            server = smtp.return_value.__enter__.return_value

            SmtpBackend(
                host="relay.ufps.edu.co",
                port=587,
                user="",
                password="",
                sender="dpto@ufps.edu.co",
                sender_name="Departamento",
            ).send(email)

        server.login.assert_not_called()
        server.send_message.assert_called_once()


class TestBackendSelection:
    """Which transport a deployment ends up with."""

    def test_console_by_default(self, monkeypatch):
        monkeypatch.setattr(email_sender.config, "MAIL_BACKEND", "console")

        assert isinstance(get_backend(), ConsoleBackend)

    def test_smtp_when_asked_for(self, monkeypatch):
        monkeypatch.setattr(email_sender.config, "MAIL_BACKEND", "smtp")

        assert isinstance(get_backend(), SmtpBackend)


class TestSendEmail:
    """The entry point the services call."""

    def test_does_nothing_while_mail_is_switched_off(self, email, monkeypatch):
        monkeypatch.setattr(email_sender.config, "MAIL_ENABLED", False)
        backend = MagicMock()
        monkeypatch.setattr(email_sender, "get_backend", lambda: backend)

        send_email(email)

        backend.send.assert_not_called()

    def test_hands_the_message_to_the_backend(self, email, monkeypatch):
        monkeypatch.setattr(email_sender.config, "MAIL_ENABLED", True)
        backend = MagicMock()
        monkeypatch.setattr(email_sender, "get_backend", lambda: backend)

        send_email(email)

        backend.send.assert_called_once_with(email)
