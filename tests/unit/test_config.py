"""Tests for how configuration is read out of the environment."""

import importlib

import pytest

from api.config import _env


class TestEnv:
    """Values arrive from a .env file typed by hand."""

    def test_reads_the_variable(self, monkeypatch):
        monkeypatch.setenv("EVD_TEST_VALUE", "smtp.gmail.com")

        assert _env("EVD_TEST_VALUE") == "smtp.gmail.com"

    def test_trims_a_padded_value(self, monkeypatch):
        """Test a trailing space in a .env line is invisible but travels.

        `SMTP_USER=correo@gmail.com ` reaches the SMTP login as a username with
        a space on the end, which the server rejects as wrong credentials — a
        long way from where the space was typed.
        """

        monkeypatch.setenv("EVD_TEST_VALUE", "  correo@gmail.com  ")

        assert _env("EVD_TEST_VALUE") == "correo@gmail.com"

    def test_falls_back_when_the_variable_is_empty(self, monkeypatch):
        """Test a key left blank in .env behaves as if it were absent."""

        monkeypatch.setenv("EVD_TEST_VALUE", "")

        assert _env("EVD_TEST_VALUE", "por-defecto") == "por-defecto"

    def test_falls_back_when_the_variable_is_missing(self, monkeypatch):
        monkeypatch.delenv("EVD_TEST_VALUE", raising=False)

        assert _env("EVD_TEST_VALUE", "por-defecto") == "por-defecto"


class TestMailSettings:
    """The mail block, re-read with a controlled environment."""

    @pytest.fixture(autouse=True)
    def _restore_the_module(self):
        """Put the real configuration back.

        These tests reload `api.config` with a doctored environment, and a
        reload replaces the module for everybody: without this, whichever test
        ran last would leave its fake credentials behind for the rest of the
        suite.
        """

        yield

        import api.config

        importlib.reload(api.config)

    def _reload(self, monkeypatch, **env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        import api.config

        return importlib.reload(api.config)

    def test_strips_the_spaces_google_prints_in_an_app_password(self, monkeypatch):
        """Test Google shows the app password in groups of four.

        The spaces are there to be read, not to be sent: pasted verbatim they
        turn a valid password into a rejected one.
        """

        module = self._reload(monkeypatch, SMTP_PASSWORD="abcd efgh ijkl mnop")

        assert module.config.SMTP_PASSWORD == "abcdefghijklmnop"

    def test_the_sender_defaults_to_the_account_that_authenticates(self, monkeypatch):
        """Test MAIL_FROM left blank is the common case, not a misconfiguration."""

        module = self._reload(
            monkeypatch, MAIL_FROM="", SMTP_USER="dpto@ufps.edu.co"
        )

        assert module.config.MAIL_FROM == "dpto@ufps.edu.co"

    def test_the_frontend_url_never_ends_in_a_slash(self, monkeypatch):
        """Test the links are built by concatenation, so a trailing / doubles it."""

        module = self._reload(monkeypatch, FRONTEND_URL="https://evd.ufps.edu.co/ ")

        assert module.config.FRONTEND_URL == "https://evd.ufps.edu.co"
