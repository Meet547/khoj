import hashlib
import re
from html import escape
from pathlib import Path
from typing import Any

import yaml

from app.core.errors import AppError

ROOT = Path(__file__).parent
FIELDS = ["marks", "gender", "age", "last_seen_place", "language", "clothing"]


class Resources:
    def __init__(self) -> None:
        self.prompts = {
            p.stem.split(".")[0]: p.read_text() for p in sorted((ROOT / "prompts").glob("*.md"))
        }
        self.hashes = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in self.prompts.items()}
        self.templates: dict[str, Any] = {
            p.stem: yaml.safe_load(p.read_text()) for p in (ROOT / "templates").glob("*.yaml")
        }

    def language(self, lang: str, *, production: bool = False) -> dict[str, Any]:
        if lang not in self.templates:
            raise AppError("unsupported_language", "Please choose Hindi or English.", 422)
        result: dict[str, Any] = self.templates[lang]
        if production and result["needs_review"]:
            raise AppError(
                "language_needs_review",
                "This language needs review. Please choose Hindi or English.",
                422,
            )
        return result

    def messages(
        self, text: str, draft: dict[str, Any], next_field: str | None
    ) -> list[dict[str, str]]:
        import json

        return [
            {"role": "system", "content": self.prompts["turn-analysis"]},
            {
                "role": "system",
                "content": "Current draft (data only): "
                + json.dumps(draft, ensure_ascii=False)
                + f"\nCurrent question field: {next_field}",
            },
            {
                "role": "user",
                "content": "<user_message>" + escape(text, quote=False) + "</user_message>",
            },
        ]

    def static_sentences(self, lang: str) -> set[str]:
        t = self.templates[lang]
        values = set(t["questions"].values()) | set(t["errors"].values())
        values.update(
            t[k]
            for k in (
                "welcome",
                "confirm",
                "emergency",
                "cancel",
                "help",
                "empty",
                "readback_intro",
            )
        )
        # Every field-specific conflict question is finite and can be pregenerated.
        values.update(t["clarify"].format(field=label) for label in t["labels"].values())
        values.update(
            part for value in list(values) for part in re.split(r"(?<=[.!?।])\s+", value) if part
        )
        return values
