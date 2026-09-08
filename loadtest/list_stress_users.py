"""List real uids per role from the Neon "stress-test" branch.

Locust needs a handful of real `users.uid` values to send in the
`X-Test-Uid` header (see loadtest/asgi_stress.py) so `require_roles` does a
real role check against real rows instead of a made-up id. Reads
DATABASE_URL from .env.stress.local — never touches the real .env. Writes
loadtest/stress_users.json so locustfile.py doesn't need its own DB
connection just to pick a uid per role.

    ./venv/bin/python loadtest/list_stress_users.py
"""

import json
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ENV_FILE = Path(__file__).resolve().parent.parent / ".env.stress.local"
OUTPUT_FILE = Path(__file__).resolve().parent / "stress_users.json"
PER_ROLE_LIMIT = 5


def main() -> None:
    values = dotenv_values(ENV_FILE)
    database_url = values.get("DATABASE_URL")

    if not database_url or "ep-xxxx-pooler" in database_url:
        raise SystemExit(
            f"{ENV_FILE} todavía tiene el DATABASE_URL de placeholder. "
            "Pega ahí el connection string real del branch stress-test primero."
        )

    engine = create_engine(database_url)

    query = text(
        """
        SELECT r.name AS role, u.uid
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE u.uid IS NOT NULL AND u.active IS TRUE
        ORDER BY r.name, u.id
        """
    )

    by_role: dict[str, list[str]] = {}
    with engine.connect() as conn:
        for role, uid in conn.execute(query):
            by_role.setdefault(role, []).append(uid)

    if not by_role:
        print("No se encontraron usuarios activos con uid y rol en este branch.")
        return

    for role, uids in by_role.items():
        sample = uids[:PER_ROLE_LIMIT]
        print(f"\n{role} ({len(uids)} en total, mostrando {len(sample)}):")
        for uid in sample:
            print(f"  {uid}")

    OUTPUT_FILE.write_text(
        json.dumps({role: uids[:PER_ROLE_LIMIT] for role, uids in by_role.items()}, indent=2),
        encoding="utf-8",
    )
    print(f"\nGuardado en {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
