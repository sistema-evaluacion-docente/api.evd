"""Generate a throwaway Firebase service-account cert for the local stress-test env.

`firebase_admin.credentials.Certificate()` only checks the JSON shape and
parses the private key as PEM — it never calls Google at that point. A
self-signed key is therefore enough to let `api/middlewares/auth.py` boot
without a real Firebase project. Real token verification never runs in this
environment anyway: `loadtest/asgi_stress.py` overrides `get_current_user`
before any request reaches it. Same trick as
`.github/workflows/tests.yaml`'s "Generate a throwaway Firebase service
account" step.

Run it whenever `.env.stress.local` is missing the Firebase block, or to
rotate the throwaway key:

    ./venv/bin/python loadtest/generate_stress_firebase_cert.py
"""

import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ENV_FILE = Path(__file__).resolve().parent.parent / ".env.stress.local"

FIELDS = {
    "FIREBASE_TYPE": "service_account",
    "FIREBASE_PROJECT_ID": "evd-stress-test",
    "FIREBASE_PRIVATE_KEY_ID": "stress",
    "FIREBASE_CLIENT_EMAIL": "stress@evd-stress-test.iam.gserviceaccount.com",
    "FIREBASE_CLIENT_ID": "0",
    "FIREBASE_AUTH_URI": "https://accounts.google.com/o/oauth2/auth",
    "FIREBASE_TOKEN_URI": "https://oauth2.googleapis.com/token",
    "FIREBASE_AUTH_PROVIDER_X509_CERT_URL": "https://www.googleapis.com/oauth2/v1/certs",
    "FIREBASE_CLIENT_X509_CERT_URL": (
        "https://www.googleapis.com/robot/v1/metadata/x509/"
        "stress%40evd-stress-test.iam.gserviceaccount.com"
    ),
    "FIREBASE_UNIVERSE_DOMAIN": "googleapis.com",
}


def _private_key_pem() -> str:
    """A PKCS8 PEM private key with real newlines escaped to literal ``\\n``.

    `docker-compose.stress.yaml` injects this via `env_file`, which does not
    unescape `\\n` — it passes the quoted value through as-is. `api/config.py`
    does the unescaping itself (`FIREBASE_PRIVATE_KEY.replace("\\n", "\n")`),
    same convention as the real `docker-compose.yaml`.
    """

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return pem.replace("\n", "\\n")


def main() -> None:
    values = dict(FIELDS)
    values["FIREBASE_PRIVATE_KEY"] = _private_key_pem()

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []

    written = set()
    for i, line in enumerate(lines):
        match = re.match(r"^(FIREBASE_[A-Z0-9_]+)=", line)
        if match and match.group(1) in values:
            key = match.group(1)
            lines[i] = f'{key}="{values[key]}"'
            written.add(key)

    for key, value in values.items():
        if key not in written:
            lines.append(f'{key}="{value}"')

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Certificado Firebase de prueba escrito en {ENV_FILE}")


if __name__ == "__main__":
    main()
