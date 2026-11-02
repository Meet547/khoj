"""Create development secrets once, without printing them or overwriting an existing file."""

import base64
import os
import secrets
from pathlib import Path


def main() -> None:
    destination = Path(".env")
    with open(destination, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        stream.write("KHOJ_ENV=development\nDEMO_AUTH=1\n")
        stream.write(
            "DATABASE_URL=postgresql+asyncpg://khoj:khoj@localhost:5432/khoj\nREDIS_URL=redis://localhost:6379/0\n"
        )
        stream.write("JWT_SECRET=" + secrets.token_urlsafe(48) + "\n")
        stream.write("PHONE_HMAC_SECRET=" + secrets.token_urlsafe(48) + "\n")
        stream.write(
            "PHONE_ENC_KEY=" + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode() + "\n"
        )
    print("Created .env with private local development keys.")


if __name__ == "__main__":
    main()
