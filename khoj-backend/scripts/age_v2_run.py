"""Owner-run evaluation. Invoke from khoj-backend with python -m scripts.age_v2_run."""

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date
from pathlib import Path
from typing import Any, NoReturn, TextIO, TypedDict
from unicodedata import normalize

import httpx
from dotenv import dotenv_values
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.errors import AppError
from app.graph.resources import Resources
from app.graph.service import IntakeService
from app.graph.triage import SKIP, triage
from app.integrations.ollama import OllamaClient
from app.llm import LLM, LLMResult
from app.privacy import redact
from app.schemas import is_grounded

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
CORPUS = BACKEND / "evals/heldout_v2"
PREREG = ROOT / "docs/evaluation/age_v2_preregistration.md"
REPORT = ROOT / "docs/evaluation/age_v2.md"
DETAIL = ROOT / "artifacts/speech-eval/age_v2_detail_v2log.jsonl"
DRY_RUN_MARKER = DETAIL.with_name(".dryrun_ok")
PREREG_HASH = "3b7fad2511507ea255e5981dcbf69b353a25e8c2549be7a1e218c983fab088af"
CORPUS_HASHES = {
    "cases": "1e3832f4cd3f0be29f5fdb3a6a9a813c29946019147950a91b13365488a6c993",
    "labels": "86628bbf0f78f5c5249e56cea46f06faa42f8e343346d31810d07d75268b6366",
}
V3_CORPUS = BACKEND / "evals/heldout_v3"
V3_PREREG_HASH = "a3f85aadd6c21fa5b2469047bfac420017ee9ebd628abe8ce81e1e7b4457d9de"
V3_CORPUS_HASHES = {
    "cases": "dc1f11bbc9b3db1eabda544f3197a4a8838ecd6f02847532871b4d2edcf55914",
    "labels": "a81ffbbf2b637b7d5f4637aaabd0b4eb20172bdfa4709219d713db7d367d6976",
}
EXTRACTION_CAP = 120
ATTEMPT_CAP = 170
BANNER = "Owner-labelled, unreviewed held-out labels. Promotion blocked pending reviewer sign-off."
LOCAL_PORT = 5432
TCP_CHECK = "TCP reachable at localhost:5432"
LOGIN_CHECK = "login accepted for role khoj"
DATABASE_CHECK = "current database is khoj_eval"
PORT_CHECK = "inet_server_port() is 5432"
USER_CHECK = "current_user is khoj"
FIELDS = {
    "name": ("name",),
    "relation": ("relation",),
    "gender": ("gender",),
    "last_seen_place": ("last_seen_place",),
    "last_seen_time": ("last_seen_time",),
    "height_build": ("height", "build"),
    "marks": ("marks",),
    "clothing": ("clothing",),
    "language_spoken": ("language",),
    "health_or_special_needs": ("conditions",),
}


class StopRun(Exception):
    """Safe diagnostic with no connection settings or case content."""


@dataclass(frozen=True)
class Evaluation:
    corpus: Path
    prereg: Path
    prereg_hash: str
    corpus_hashes: dict[str, str]
    case_count: int
    repeat_cases: int
    report: Path
    detail: Path
    marker: Path

    @property
    def is_v3(self) -> bool:
        return self.corpus == V3_CORPUS


def evaluation_config(
    corpus: Path = CORPUS, report: Path | None = None, detail: Path | None = None
) -> Evaluation:
    corpus = corpus.resolve()
    if corpus == CORPUS:
        marker = detail.with_name(".dryrun_ok") if detail else DRY_RUN_MARKER
        return Evaluation(
            corpus,
            PREREG,
            PREREG_HASH,
            CORPUS_HASHES,
            45,
            5,
            report or REPORT,
            detail or DETAIL,
            marker,
        )
    if corpus == V3_CORPUS:
        detail = detail or DETAIL.with_name("age_v3_detail_v2log.jsonl")
        return Evaluation(
            corpus,
            ROOT / "docs/evaluation/age_v3_preregistration.md",
            V3_PREREG_HASH,
            V3_CORPUS_HASHES,
            60,
            0,
            report or REPORT.with_name("age_v3.md"),
            detail,
            detail.parent / "heldout_v3" / ".dryrun_ok",
        )
    raise StopRun("Unsupported frozen corpus directory")


class Case(TypedDict):
    item_id: str
    lang: str
    category: str
    text: str


@dataclass(frozen=True)
class TurnPlan:
    case: Case
    schema: str
    repeat: int = 0

    @property
    def item_id(self) -> str:
        return self.case["item_id"]

    @property
    def extracts(self) -> bool:
        source = self.case["text"]
        return bool(source.strip()) and triage(source) is None and not SKIP.fullmatch(source)


def load_plan(config: Evaluation | None = None) -> tuple[list[TurnPlan], dict[str, Any]]:
    config = config or evaluation_config()
    if hashlib.sha256(config.prereg.read_bytes()).hexdigest() != config.prereg_hash:
        raise StopRun("Preregistration hash mismatch")
    rows = {}
    for name, expected_hash in config.corpus_hashes.items():
        data = (config.corpus / f"{name}.jsonl").read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise StopRun(f"Corpus hash mismatch for {name}")
        rows[name] = [json.loads(line) for line in data.splitlines()]
    cases = sorted(rows["cases"], key=lambda case: case["item_id"])
    labels = {row["item_id"]: row["expected"] for row in rows["labels"]}
    if (
        len(cases) != config.case_count
        or len(labels) != config.case_count
        or {case["item_id"] for case in cases} != labels.keys()
    ):
        raise StopRun("Corpus case IDs")
    messy = [case for case in cases if case["category"] == "messy"][: config.repeat_cases]
    if len(messy) != config.repeat_cases:
        raise StopRun("Repeat case count")
    plan = [TurnPlan(case, schema) for schema in ("v1", "v2") for case in cases]
    plan.extend(TurnPlan(case, "v2", repeat) for case in messy for repeat in (1, 2))
    return plan, labels


def planned_extractions(plan: list[TurnPlan]) -> int:
    count = sum(turn.extracts for turn in plan)
    if count > EXTRACTION_CAP or count > ATTEMPT_CAP:
        raise StopRun("Planned calls exceed the caps")
    return count


def identity_failure(name: str) -> NoReturn:
    print(f"FAIL {name}")
    raise StopRun() from None


def identity_check(name: str, passed: bool) -> None:
    if not passed:
        identity_failure(name)
    print(f"PASS {name}")


def evaluation_url() -> URL:
    try:
        raw = dotenv_values(BACKEND / ".env.eval", interpolate=False).get("EVAL_DATABASE_URL")
        url = make_url(raw) if raw else None
    except Exception:
        url = None
    if (
        url is None
        or url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or url.host != "localhost"
        or url.query
        or url.port not in (None, LOCAL_PORT)
    ):
        identity_failure(TCP_CHECK)
    if url.username != "khoj":
        identity_failure(LOGIN_CHECK)
    if url.database != "khoj_eval":
        identity_failure(DATABASE_CHECK)
    return url.set(drivername="postgresql+asyncpg", port=LOCAL_PORT)


async def check_identity(engine: AsyncEngine) -> None:
    try:
        async with asyncio.timeout(5):
            _, writer = await asyncio.open_connection("localhost", LOCAL_PORT)
            writer.close()
            await writer.wait_closed()
    except OSError:
        identity_failure(TCP_CHECK)
    identity_check(TCP_CHECK, True)

    try:
        connection = await engine.connect()
    except Exception:
        identity_failure(LOGIN_CHECK)
    try:
        identity_check(LOGIN_CHECK, True)
        try:
            result = await connection.execute(
                text("select current_database(), current_user, inet_server_port()")
            )
            database, user, port = result.one()
        except Exception:
            identity_failure(DATABASE_CHECK)
        identity_check(DATABASE_CHECK, database == "khoj_eval")
        identity_check(PORT_CHECK, port == LOCAL_PORT)
        identity_check(USER_CHECK, user == "khoj")
    finally:
        await connection.close()


def dry_run_fingerprint(url: URL, key: str, config: Evaluation | None = None) -> str:
    message = url.render_as_string(hide_password=False)
    if config is not None and (config.is_v3 or config.report != REPORT or config.detail != DETAIL):
        message += "\n" + json.dumps(
            [config.prereg_hash, str(config.corpus), str(config.report), str(config.detail)]
        )
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def require_dry_run(fingerprint: str, marker: Path | None = None) -> None:
    marker = marker or DRY_RUN_MARKER
    try:
        today = date.fromtimestamp(marker.stat().st_mtime) == date.today()
        saved = marker.read_bytes()
    except OSError:
        today, saved = False, b""
    if not today or not hmac.compare_digest(saved, fingerprint.encode()):
        raise StopRun("Run --dry-run successfully today with the same evaluation configuration")


def print_plan(plan: list[TurnPlan], label_count: int) -> None:
    calls = planned_extractions(plan)
    primary = Counter(turn.schema for turn in plan if not turn.repeat)
    primary_count = sum(primary.values())
    print(
        f"Cases {label_count}, primary turns {primary_count}, repeat turns {len(plan) - primary_count}"
    )
    if not any(turn.repeat for turn in plan):
        print(f"Primary turns by schema: v1 {primary['v1']}, v2 {primary['v2']}")
    print(f"Planned extractions {calls}/{EXTRACTION_CAP}")
    print(
        f"Planned initial chat attempts {calls}/{ATTEMPT_CAP}; retries, repairs and fallbacks share the cap"
    )


@dataclass
class Budget:
    extractions: int = 0
    attempts: int = 0

    def reserve_extraction(self) -> None:
        if self.extractions >= EXTRACTION_CAP:
            raise StopRun("Extraction cap reached")
        self.extractions += 1

    def reserve_attempt(self) -> None:
        if self.attempts >= ATTEMPT_CAP:
            raise StopRun("Chat attempt cap reached")
        self.attempts += 1


class AuditedLLM(LLM):
    """Use the production router, with an evaluation budget at the actual call boundary."""

    def __init__(self, client: OllamaClient, cfg: dict[str, Any], budget: Budget):
        super().__init__(client, cfg)
        self.budget = budget
        self.reset_turn()

    def reset_turn(self) -> None:
        self.attempts: list[dict[str, Any]] = []
        self.extracted: dict[str, Any] = {}

    async def run(self, *args: Any, **kwargs: Any) -> LLMResult:
        self.budget.reserve_extraction()
        result = await super().run(*args, **kwargs)
        if result.parsed is not None:
            # Keep the response's field presence and spelling, including explicit nulls.
            raw = json.loads(result.text)
            self.extracted = {
                name: raw[name]
                for name in ("intent", "age_min", "age_max", "age_evidence")
                if name in raw and name in type(result.parsed).model_fields
            }
            if "fields" in raw:
                self.extracted["fields"] = [
                    {name: item[name] for name in ("name", "value", "evidence")}
                    for item in raw["fields"]
                ]
        return result

    async def _attempt(
        self,
        model: str,
        msgs: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        role_cfg: dict[str, Any],
        attempts: list[dict[str, Any]],
        role: str,
        repair: bool,
        retry: int,
        chain_index: int,
    ) -> dict[str, Any]:
        self.budget.reserve_attempt()
        self.attempts = attempts
        return await super()._attempt(
            model, msgs, schema, role_cfg, attempts, role, repair, retry, chain_index
        )


@dataclass(frozen=True)
class TurnResult:
    turn: TurnPlan
    draft: dict[str, Any]
    age_drop: str | None = None
    model_unavailable: bool = False
    kept: list[dict[str, Any]] = dataclass_field(default_factory=list)

    @property
    def age(self) -> tuple[int, int] | None:
        field = self.draft.get("age")
        if not field:
            return None
        pattern = r"(\d+)(?:-(\d+))?" if self.turn.schema == "v2" else r"(\d+)"
        value = re.fullmatch(pattern, field["value"].strip())
        if not value:
            return None
        try:
            low = int(value[1])
            high = int(value[2]) if self.turn.schema == "v2" and value[2] else low
        except ValueError:
            return None
        return low, high


async def run_turn(service: IntakeService, turn: TurnPlan) -> TurnResult:
    lang = "hi" if turn.case["lang"] == "hinglish" else turn.case["lang"]
    token = secrets.token_urlsafe(32)
    sid = await service.create("missing", lang, token, None)
    async with service.locked(sid, token, None) as session:
        try:
            state = await service.run_turn(
                session,
                {"text": turn.case["text"], "mode": "text", "stt_ms": 0, "lang": lang},
                "turn:age-v2-evaluation",
            )
        except AppError as exc:
            if exc.code != "model_unavailable":
                raise
            return TurnResult(turn, {}, model_unavailable=True)
    return TurnResult(
        turn, state["draft"], state.get("age_grounding_drop"), kept=state.get("kept", [])
    )


def age_correct(result: TurnResult, label: dict[str, Any] | None) -> bool:
    bounds = result.age
    if bounds is None or label is None:
        return False
    expected = label["value"]
    return bool(bounds[0] <= expected["max"] and expected["min"] <= bounds[1])


@dataclass
class Score:
    true_positives: int = 0
    labelled: int = 0
    emitted: int = 0
    wrong: int = 0
    exact: int = 0
    total: int = 0

    def add(self, labelled: bool, emitted: bool, matches: bool) -> None:
        self.true_positives += labelled and matches
        self.labelled += labelled
        self.emitted += emitted
        self.wrong += emitted and not matches
        self.exact += matches or (not labelled and not emitted)
        self.total += 1


def folded(value: str) -> str:
    return normalize("NFC", value).casefold()


def score_rows(rows: list[TurnResult], labels: dict[str, Any], field: str) -> Score:
    score = Score()
    for row in rows:
        label = labels[row.turn.item_id][field]
        if field == "age":
            score.add(label is not None, "age" in row.draft, age_correct(row, label))
        else:
            values = [row.draft[key]["value"] for key in FIELDS[field] if key in row.draft]
            matches = bool(
                label
                and values
                and all(folded(value) == folded(label["value"]) for value in values)
            )
            score.add(label is not None, bool(values), matches)
    return score


def grounding_log(result: TurnResult, extracted: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = []
    source = result.turn.case["text"]
    for index, proposal in enumerate(extracted.get("fields", [])):
        name = proposal["name"]
        if name == "age" and result.turn.schema == "v2":
            decision, reason = None, "legacy_age_ignored"
        elif proposal in result.kept:
            decision, reason = "kept", "production_grounding_passed"
        elif not is_grounded(proposal["evidence"], source):
            decision, reason = "quote_missing", "production_quote_check_failed"
        else:
            decision, reason = "blank_dropped", "blank_value"
        decisions.append(
            {"field": name, "proposal_index": index, "decision": decision, "reason": reason}
        )
    if any(extracted.get(name) is not None for name in ("age_min", "age_max", "age_evidence")):
        decision = result.age_drop or "kept"
        reason = {
            "kept": "production_grounding_passed",
            "quote_missing": "exact_quote_check_failed",
            "number_missing": "range_not_supported_by_quote",
        }[decision]
        decisions.append(
            {"field": "age", "proposal_index": None, "decision": decision, "reason": reason}
        )
    return decisions


def comparison_log(result: TurnResult, labels: dict[str, Any]) -> dict[str, Any]:
    comparisons = {}
    for name, label in labels[result.turn.item_id].items():
        score = score_rows([result], labels, name)
        if label is None:
            outcome = "null_wrong_value" if score.emitted else "null_correct"
        elif score.true_positives:
            outcome = "correct"
        else:
            outcome = "wrong_value" if score.emitted else "omitted"
        comparisons[name] = {
            "label_value": label["value"] if label is not None else None,
            "outcome": outcome,
        }
    return comparisons


def safe_log_value(value: Any, source: str, private: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        if source:
            normalized = normalize("NFC", value)
            if source in normalized:
                value = normalized.replace(source, "[TRANSCRIPT]")
        for secret in private:
            if secret:
                value = value.replace(secret, "[SECRET]")
        return redact(value)
    if type(value) is int:
        sanitized = redact(str(value))
        return value if sanitized == str(value) else sanitized
    if isinstance(value, dict):
        return {key: safe_log_value(item, source, private) for key, item in value.items()}
    if isinstance(value, list):
        return [safe_log_value(item, source, private) for item in value]
    return value


def log_turn(
    log: TextIO,
    llm: AuditedLLM,
    result: TurnResult,
    labels: dict[str, Any],
    private: tuple[str, ...],
    *,
    completed: bool = True,
) -> None:
    turn = result.turn
    record = {
        "item_id": turn.item_id,
        "schema": turn.schema,
        "turn_type": "repeat" if turn.repeat else "primary",
        "repeat": turn.repeat,
        "extracted": llm.extracted,
        "grounding": grounding_log(result, llm.extracted) if completed else [],
        "comparison": comparison_log(result, labels) if completed else {},
        "attempts": [{"outcome": "error", **attempt} for attempt in llm.attempts],
    }
    for name in ("extracted", "comparison"):
        record[name] = safe_log_value(
            record[name], normalize("NFC", turn.case["text"]).strip(), private
        )
    log.write(json.dumps(record, ensure_ascii=False) + "\n")
    log.flush()


def rate(count: int, denominator: int) -> str:
    return f"{count / denominator:.1%} ({count}/{denominator})" if denominator else "N/A (0/0)"


def write_report(
    results: list[TurnResult], labels: dict[str, Any], budget: Budget, config: Evaluation
) -> str:
    signed_off = any(
        line.startswith("Reviewer status: signed off by ")
        for line in (config.corpus / "MANIFEST.md").read_text().splitlines()
    )
    version = "v3" if config.is_v3 else "v2"
    primary = {
        schema: [row for row in results if row.turn.schema == schema and row.turn.repeat == 0]
        for schema in ("v1", "v2")
    }
    lines = [] if config.is_v3 and signed_off else [BANNER, ""]
    lines.extend(
        [
            f"# Age {version} held-out evaluation",
            "",
            f"- Preregistration SHA-256 `{config.prereg_hash}`",
            f"- Extractions {budget.extractions}/{EXTRACTION_CAP}",
            f"- Ollama chat attempts {budget.attempts}/{ATTEMPT_CAP}",
            "- Gnani requests 0",
            "- Default schema v1",
            "- Primary case IDs " + ", ".join(sorted(labels)),
            "",
            "## Age",
            "",
        ]
    )
    age_scores = {}
    for schema, rows in primary.items():
        for lang in (None, *sorted({row.turn.case["lang"] for row in rows})):
            group = rows if lang is None else [row for row in rows if row.turn.case["lang"] == lang]
            score = score_rows(group, labels, "age")
            if lang is None:
                age_scores[schema] = score
            lines.append(
                f"- {schema} {lang or 'overall'} (n={len(group)}) — "
                f"recall {rate(score.true_positives, score.labelled)}, "
                f"precision {rate(score.true_positives, score.emitted)}"
            )

    lines.extend(["", "## Other fields", ""])
    field_ok = True
    gender_wrong = {}
    for field in FIELDS:
        v1, v2 = (score_rows(rows, labels, field) for rows in primary.values())
        # Both versions have the same labelled denominator.
        field_ok &= 20 * (v1.true_positives - v2.true_positives) <= v1.labelled
        if field == "gender":
            gender_wrong = {"v1": v1.wrong, "v2": v2.wrong}
        for schema, score in (("v1", v1), ("v2", v2)):
            lines.append(
                f"- {field}, {schema} — recall {rate(score.true_positives, score.labelled)}, "
                f"exact accuracy {rate(score.exact, score.total)}, wrong values {score.wrong}"
            )

    repeats = [row for row in results if row.turn.repeat]
    if config.repeat_cases:
        lines.extend(["", "## Repeat spread", ""])
    for case_id in sorted({row.turn.item_id for row in repeats}):
        rows = [row for row in repeats if row.turn.item_id == case_id]
        label = labels[case_id]["age"]
        correct = sum(age_correct(row, label) for row in rows)
        bounds = [row.age for row in rows if row.age is not None]
        spread = (
            f"{abs(bounds[0][0] - bounds[1][0])} lower, {abs(bounds[0][1] - bounds[1][1])} upper"
            if len(bounds) == 2
            else "unavailable"
        )
        lines.append(
            f"- {case_id} — {correct}/2 correct, {len(bounds)}/2 emitted, bound spread {spread}"
        )

    lines.extend(["", "## Grounding and model failures", ""])
    groups = list(primary.items())
    if config.repeat_cases:
        groups.append(("v2 repeat", repeats))
    for group_name, rows in groups:
        drops = Counter(row.age_drop for row in rows)
        unavailable = sum(row.model_unavailable for row in rows)
        lines.append(
            f"- {group_name} — quote_missing {drops['quote_missing']}, "
            f"number_missing {drops['number_missing']}, model unavailable {unavailable}"
        )

    age = age_scores["v2"]
    age_ok = age.labelled > 0 and 4 * age.true_positives >= 3 * age.labelled
    gender_ok = gender_wrong["v2"] == 0
    if not signed_off:
        promotion = "promotion_blocked: unreviewed labels"
    elif age_ok and field_ok and gender_ok:
        promotion = "eligible for promotion"
    else:
        promotion = "promotion_blocked: performance criteria"
    lines.extend(["", "## Promotion", ""])
    for name, passed in (
        ("Age recall at least 75%", age_ok),
        ("All other field recall drops at most five points", field_ok),
        ("Zero v2 gender wrong values", gender_ok),
        ("Reviewer sign-off", signed_off),
    ):
        lines.append(f"- {name} — {'met' if passed else 'unmet'}")
    lines.extend(["", f"`{promotion}`", ""])
    config.report.write_text("\n".join(lines), encoding="utf-8")
    return promotion


async def evaluate(
    url: URL,
    engine: AsyncEngine,
    key: str,
    plan: list[TurnPlan],
    labels: dict[str, Any],
    budget: Budget,
    config: Evaluation,
) -> list[TurnResult]:
    config.detail.parent.mkdir(parents=True, exist_ok=True)
    # A partial or completed log is retained. Requiring a fresh path prevents
    # accidental reruns and overlapping owners from spending against the same approval.
    try:
        turn_log = config.detail.open("x", encoding="utf-8")
    except FileExistsError:
        raise StopRun("Turn log already exists") from None
    with turn_log:
        client = OllamaClient(
            "https://ollama.com", key, transport=httpx.AsyncHTTPTransport(trust_env=False)
        )
        redis = Redis(host="localhost", port=6379)
        settings = Settings.model_construct(
            database_url=url.render_as_string(hide_password=False), env="production"
        )
        llm = AuditedLLM(client, settings.models(), budget)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        resources = Resources()
        private = (key, url.password or "")
        results = []
        try:
            for schema in ("v1", "v2"):
                service = IntakeService(
                    settings.model_copy(update={"extraction_schema": schema}),
                    factory,
                    redis,
                    llm,
                    resources,
                )
                try:
                    for turn in (item for item in plan if item.schema == schema):
                        llm.reset_turn()
                        try:
                            result = await run_turn(service, turn)
                        except (Exception, asyncio.CancelledError):
                            if llm.attempts:
                                log_turn(
                                    turn_log,
                                    llm,
                                    TurnResult(turn, {}),
                                    labels,
                                    private,
                                    completed=False,
                                )
                            raise
                        log_turn(turn_log, llm, result, labels, private)
                        results.append(result)
                finally:
                    await service.close()
        finally:
            await redis.aclose()
            await client.aclose()
    return results


async def run(dry_run: bool, config: Evaluation | None = None) -> None:
    config = config or evaluation_config()
    if dry_run:
        config.marker.unlink(missing_ok=True)
    plan, labels = load_plan(config)
    planned_extractions(plan)
    url = evaluation_url()
    # Prevent libpq (durable checkpoints) and asyncpg from using inherited
    # routing, service or authentication overrides.
    for name in tuple(os.environ):
        if name.startswith("PG"):
            del os.environ[name]
    os.environ["PGPASSFILE"] = os.devnull
    engine = create_async_engine(url, hide_parameters=True, connect_args={"timeout": 5})
    budget = Budget()
    identity_verified = False
    try:
        await check_identity(engine)
        identity_verified = True
        key = dotenv_values(BACKEND / ".env", interpolate=False).get("OLLAMA_API_KEY")
        if not key or not key.strip():
            raise StopRun("OLLAMA_API_KEY missing")
        print("OLLAMA_API_KEY present")
        fingerprint = dry_run_fingerprint(url, key, config)
        if not dry_run:
            require_dry_run(fingerprint, config.marker)
        print_plan(plan, len(labels))
        if not dry_run:
            results = await evaluate(url, engine, key, plan, labels, budget, config)
            print(write_report(results, labels, budget, config))
            config.marker.unlink(missing_ok=True)
    finally:
        await engine.dispose()
        if identity_verified:
            print(
                f"Extractions {budget.extractions}; "
                f"Ollama chat attempts {budget.attempts}; Gnani requests 0"
            )
    if dry_run:
        config.marker.parent.mkdir(parents=True, exist_ok=True)
        config.marker.write_text(fingerprint)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--corpus", type=Path, default=CORPUS, help="Frozen corpus directory")
    parser.add_argument("--report", type=Path, help="Markdown report output path")
    parser.add_argument("--detail", type=Path, help="JSONL turn log output path")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    # Provider, graph and DB errors can include text or credentials. Only
    # runner-authored diagnostics and aggregate counts go to the terminal.
    logging.disable(logging.CRITICAL)
    try:
        asyncio.run(run(args.dry_run, evaluation_config(args.corpus, args.report, args.detail)))
    except StopRun as exc:
        raise SystemExit(str(exc) or 1) from None
    except KeyboardInterrupt:
        raise SystemExit("Interrupted") from None
    except Exception as exc:
        raise SystemExit(f"Evaluation stopped ({type(exc).__name__})") from None


if __name__ == "__main__":
    main()
