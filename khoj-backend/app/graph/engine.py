import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models import Turn
from app.db.repo.intake import IntakeRepository
from app.graph.age_v2 import AGE_INSTRUCTIONS, ExtractionV2, ground_age
from app.graph.resources import FIELDS, Resources
from app.graph.state import FieldState, IntakeState
from app.graph.triage import SKIP, triage
from app.llm import LLM, LLMUnavailable
from app.schemas import Extraction, FieldValue, ground

logger = logging.getLogger("khoj")


class IntakeNodes:
    def __init__(
        self,
        llm: LLM,
        resources: Resources,
        factory: async_sessionmaker[AsyncSession],
        enqueue: Callable[[str], Awaitable[bool]],
        extraction_schema: Literal["v1", "v2"] = "v1",
    ):
        self.llm, self.resources, self.factory, self.enqueue = llm, resources, factory, enqueue
        self.extraction_schema = extraction_schema
        self.prompt_hash = resources.hashes["turn-analysis"]
        if extraction_schema == "v2":
            self.age_prompt_suffix = "\n\n" + AGE_INSTRUCTIONS
            self.prompt_hash = hashlib.sha256(
                (resources.prompts["turn-analysis"] + self.age_prompt_suffix).encode()
            ).hexdigest()

    def load_draft(self, state: IntakeState) -> dict[str, Any]:
        current = state["current"]
        safety = triage(current["text"])
        return {
            "lang": current.get("lang", state["lang"]),
            "transcripts": [*state["transcripts"], current["text"]],
            "request_id": current["id"],
            "triage": safety,
            "stopped": safety == "cancel",
            "stage": "collecting",
            "readback_text": None,
            "extraction": {},
            "kept": [],
            "ungrounded": [],
            **({"age_grounding_drop": None} if self.extraction_schema == "v2" else {}),
            "reply": "",
            "model": "",
            "trail": [],
            "attempts": [],
            "llm_ms": 0,
            "degraded": False,
            "prompt_hash": self.prompt_hash,
        }

    def safety_reply(self, state: IntakeState) -> dict[str, Any]:
        t = self.resources.templates[state["lang"]]
        key = state.get("triage") or "empty"
        return {
            "reply": t[key],
            "next_field": state.get("next_field") if key in {"help", "empty"} else None,
        }

    async def analyze_turn(self, state: IntakeState) -> dict[str, Any]:
        current = state["current"]
        if current.get("edit"):
            edited = Extraction(
                intent="correction",
                fields=[
                    FieldValue(
                        name=current["edit"], value=current["text"], evidence=current["text"]
                    )
                ],
            )
            return {"extraction": edited.model_dump()}
        if SKIP.fullmatch(current["text"]):
            return {"extraction": Extraction(intent="skip").model_dump()}
        started = time.monotonic()
        messages = self.resources.messages(current["text"], state["draft"], state.get("next_field"))
        schema_model: type[Extraction] = Extraction
        if self.extraction_schema == "v2":
            schema_model = ExtractionV2
            messages[0]["content"] += self.age_prompt_suffix
        try:
            result = await self.llm.run(
                "turn",
                messages,
                schema_model=schema_model,
                lang=state["lang"],
            )
        except LLMUnavailable as exc:
            # Preserve failed attempts too; there is no successful node update to
            # checkpoint when analysis raises. Reuse the existing turns trace JSON.
            failed = {
                **state,
                "reply": self.resources.templates[state["lang"]]["errors"]["model"],
                "trail": exc.trail,
                "attempts": exc.attempts,
                "llm_ms": int((time.monotonic() - started) * 1000),
            }
            await self.record_turn(cast(IntakeState, failed))
            raise AppError(
                "model_unavailable",
                self.resources.templates[state["lang"]]["errors"]["model"],
                503,
                retryable=True,
            ) from exc
        extraction = cast(Extraction | None, result.parsed) or Extraction(intent="other")
        # Model intents can suggest wording; they can never confirm, persist or enqueue.
        return {
            "extraction": extraction.model_dump(),
            "model": result.model,
            "trail": result.trail,
            "attempts": result.attempts,
            "llm_ms": result.latency_ms,
            "degraded": result.degraded,
        }

    def ground(self, state: IntakeState) -> dict[str, Any]:
        text = state["current"]["text"]
        raw = state["extraction"]
        extraction = Extraction.model_validate(raw)
        age_drop = None
        if self.extraction_schema == "v2" and "age_min" in raw:
            structured = ExtractionV2.model_validate(raw)
            extraction.fields = [field for field in extraction.fields if field.name != "age"]
            age, age_drop = ground_age(text, structured)
        else:
            age = None
        kept, dropped = ground(text, extraction)
        if age is not None:
            kept.append(age)
        if age_drop is not None:
            logger.info("intake_age_ungrounded", extra={"reason": age_drop})
        if dropped:
            logger.info("intake_fields_ungrounded")
        return {
            "kept": [f.model_dump() for f in kept],
            "ungrounded": [f.model_dump() for f in dropped],
            **({"age_grounding_drop": age_drop} if self.extraction_schema == "v2" else {}),
        }

    def merge(self, state: IntakeState) -> dict[str, Any]:
        draft, conflicts = dict(state["draft"]), dict(state.get("conflicts", {}))
        correction = state["extraction"].get("intent") == "correction"
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in state.get("kept", []):
            grouped.setdefault(item["name"], []).append(item)
        for name, items in grouped.items():
            # Duplicate, contradictory values inside one model output are ambiguous too.
            values = {f["value"].strip().casefold() for f in items}
            item = items[-1]
            confidence = (
                "confirm"
                if state["current"]["mode"] == "voice"
                and name in {"name", "age", "last_seen_place"}
                else "high"
            )
            field: FieldState = {
                "value": item["value"],
                "evidence": item["evidence"],
                "source_turn": len(state["transcripts"]),
                "confidence": cast(Any, confidence),
                "confirmed": bool(state["current"].get("edit")),
            }
            if len(values) > 1:
                field["confidence"] = "confirm"
                conflicts[name] = field
            elif (
                correction
                or name not in draft
                or draft[name]["value"].casefold() == item["value"].casefold()
            ):
                draft[name] = field
                conflicts.pop(name, None)
            else:
                field["confidence"] = "confirm"
                conflicts[name] = field
        # A repeated answer to a conflict is explicit disambiguation, even without "correction".
        target = state.get("next_field")
        if (
            target
            and f"conflict:{target}" in state["asked"]
            and target in grouped
            and len(grouped[target]) == 1
        ):
            if target in conflicts:
                draft[target] = conflicts.pop(target)
                draft[target]["confidence"] = (
                    "confirm"
                    if state["current"]["mode"] == "voice"
                    and target in {"name", "age", "last_seen_place"}
                    else "high"
                )
        return {"draft": draft, "conflicts": conflicts}

    def gap_check(self, state: IntakeState) -> dict[str, Any]:
        conflicts = [f for f in state.get("conflicts", {}) if f"conflict:{f}" not in state["asked"]]
        gaps = conflicts + [
            f for f in FIELDS if f not in state["draft"] and f not in state["asked"]
        ]
        if state["current"].get("readback"):
            gaps = []
        return {"gaps": gaps}

    def ask_next(self, state: IntakeState) -> dict[str, Any]:
        target = state["gaps"][0]
        t = self.resources.templates[state["lang"]]
        conflict = target in state.get("conflicts", {})
        reply = (
            t["clarify"].format(field=t["labels"][target]) if conflict else t["questions"][target]
        )
        return {
            "asked": [*state["asked"], f"conflict:{target}" if conflict else target],
            "next_field": target,
            "reply": reply,
            "stage": "collecting",
        }

    def readback(self, state: IntakeState) -> dict[str, Any]:
        t = self.resources.templates[state["lang"]]
        parts = [t["readback_intro"]]
        parts.extend(
            t["readback_item"].format(field=t["labels"][key], value=value["value"])
            for key, value in state["draft"].items()
        )
        if state.get("conflicts"):
            parts.append(t["errors"]["conflict"])
        parts.append(t["confirm"])
        reply = " ".join(parts)
        return {"reply": reply, "readback_text": reply, "stage": "readback", "next_field": None}

    async def record_turn(self, state: IntakeState) -> dict[str, Any]:
        values = dict(
            session_id=state["session_id"],
            idx=len(state["transcripts"]),
            input_mode=state["current"]["mode"],
            transcript_original=state["current"]["text"],
            transcript_lang=state["lang"],
            reply_text=state["reply"],
            ungrounded=state.get("ungrounded", []),
            stt_ms=state["current"].get("stt_ms", 0),
            llm_ms=state.get("llm_ms", 0),
            models={
                "turn": state.get("model"),
                "prompt_hash": state.get("prompt_hash"),
                "request_id": state.get("request_id"),
                "trail": state.get("trail", []),
                "attempts": state.get("attempts", []),
            },
        )
        async with self.factory() as db, db.begin():
            statement = insert(Turn).values(**values)
            await db.execute(
                statement.on_conflict_do_update(index_elements=["session_id", "idx"], set_=values)
            )
        return {}

    def confirm(self, state: IntakeState) -> Command[Any]:
        answer = interrupt(
            {"readbackText": state.get("readback_text"), "sessionId": state["session_id"]}
        )
        if answer.get("action") == "change":
            return Command(update={"current": answer["current"]}, goto="load_draft")
        if answer.get("action") != "save" or state.get("conflicts"):
            raise AppError("confirmation_required", "Please review the details before saving.", 409)
        return Command(
            update={
                "owner_id": answer["owner_id"],
                "owner_role": answer["owner_role"],
                "consent": answer["consent"],
                "stage": "confirmed",
                "draft": {k: {**v, "confirmed": True} for k, v in state["draft"].items()},
            },
            goto="require_auth",
        )

    def require_auth(self, state: IntakeState) -> dict[str, Any]:
        if not state.get("owner_id") or not state.get("consent"):
            raise AppError("unauthorized", "Please sign in and confirm consent.", 401)
        return {}

    async def persist(self, state: IntakeState) -> dict[str, Any]:
        result = await IntakeRepository(self.factory).persist(cast(dict[str, Any], state))
        return {**result, "stage": "saved"}

    async def enqueue_match(self, state: IntakeState) -> dict[str, Any]:
        return {"queued": await self.enqueue(state["person_id"])}


def build_graph(nodes: IntakeNodes, checkpointer: BaseCheckpointSaver[Any]) -> Any:
    builder = StateGraph(IntakeState)
    for name in (
        "load_draft",
        "safety_reply",
        "analyze_turn",
        "ground",
        "merge",
        "gap_check",
        "ask_next",
        "readback",
        "record_turn",
        "confirm",
        "require_auth",
        "persist",
        "enqueue_match",
    ):
        builder.add_node(name, getattr(nodes, name))
    builder.add_edge(START, "load_draft")
    builder.add_conditional_edges(
        "load_draft",
        lambda s: (
            "safety_reply"
            if s.get("triage") or not s["current"]["text"].strip()
            else "analyze_turn"
        ),
    )
    builder.add_edge("safety_reply", "record_turn")
    builder.add_edge("analyze_turn", "ground")
    builder.add_edge("ground", "merge")
    builder.add_edge("merge", "gap_check")
    builder.add_conditional_edges(
        "gap_check", lambda s: "ask_next" if s.get("gaps") and len(s["asked"]) < 3 else "readback"
    )
    builder.add_edge("ask_next", "record_turn")
    builder.add_edge("readback", "record_turn")
    builder.add_conditional_edges(
        "record_turn", lambda s: "confirm" if s["stage"] == "readback" else END
    )
    builder.add_edge("require_auth", "persist")
    builder.add_edge("persist", "enqueue_match")
    builder.add_edge("enqueue_match", END)
    return builder.compile(checkpointer=checkpointer)
