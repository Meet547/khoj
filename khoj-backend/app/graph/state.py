from typing import Any, Literal, NotRequired, TypedDict


class FieldState(TypedDict):
    value: str
    evidence: str
    source_turn: int
    confidence: Literal["high", "confirm"]
    confirmed: bool


class IntakeState(TypedDict):
    session_id: str
    kind: Literal["missing", "found"]
    lang: str
    draft: dict[str, FieldState]
    transcripts: list[str]
    asked: list[str]
    stage: Literal["collecting", "readback", "confirmed", "saved"]
    photo_ids: list[str]
    current: NotRequired[dict[str, Any]]
    extraction: NotRequired[dict[str, Any]]
    kept: NotRequired[list[dict[str, Any]]]
    ungrounded: NotRequired[list[dict[str, Any]]]
    age_grounding_drop: NotRequired[Literal["quote_missing", "number_missing"] | None]
    conflicts: NotRequired[dict[str, FieldState]]
    gaps: NotRequired[list[str]]
    next_field: NotRequired[str | None]
    reply: NotRequired[str]
    readback_text: NotRequired[str | None]
    triage: NotRequired[str | None]
    stopped: NotRequired[bool]
    request_id: NotRequired[str]
    model: NotRequired[str]
    trail: NotRequired[list[str]]
    attempts: NotRequired[list[dict[str, Any]]]
    llm_ms: NotRequired[int]
    prompt_hash: NotRequired[str]
    degraded: NotRequired[bool]
    owner_id: NotRequired[str]
    owner_role: NotRequired[str]
    consent: NotRequired[bool]
    case_no: NotRequired[str]
    person_id: NotRequired[str]
    queued: NotRequired[bool]
