"""Evidence-grounded extraction. The model must quote the words it relied on; code checks the quote really
appears in what the user said. Anything it cannot ground is dropped. This is the anti-hallucination core."""

import re
from typing import Literal

from pydantic import BaseModel, Field

FieldName = Literal[
    "name",
    "relation",
    "gender",
    "age",
    "height",
    "build",
    "complexion",
    "hair",
    "marks",
    "language",
    "clothing",
    "last_seen_place",
    "last_seen_time",
    "conditions",
]


class FieldValue(BaseModel):
    name: FieldName
    value: str = Field(description="Value in plain English, as stated. Never guess.")
    evidence: str = Field(
        description="Exact words copied from the user's message that support the value."
    )


class Extraction(BaseModel):
    intent: Literal[
        "provide_details", "correction", "skip", "help", "emergency", "cancel", "other"
    ] = "provide_details"
    fields: list[FieldValue] = []


def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", " ", s.casefold()).strip()


def is_grounded(evidence: str, transcript: str, threshold: float = 0.8) -> bool:
    e, t = _norm(evidence), _norm(transcript)
    if not e:
        return False
    if e in t:
        return True
    toks = e.split()
    have = set(t.split())
    return len(toks) >= 2 and sum(w in have for w in toks) / len(toks) >= threshold


def ground(transcript: str, ex: Extraction) -> tuple[list[FieldValue], list[FieldValue]]:
    kept: list[FieldValue] = []
    dropped: list[FieldValue] = []
    for f in ex.fields:
        (kept if is_grounded(f.evidence, transcript) and f.value.strip() else dropped).append(f)
    return kept, dropped
