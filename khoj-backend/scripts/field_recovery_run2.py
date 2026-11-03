"""Preregister and execute the capped durable-intake variance evaluation."""

import argparse
import asyncio
import hashlib
import logging
import os
import secrets
from collections import Counter
from pathlib import Path
from uuid import UUID

from fakeredis.aioredis import FakeRedis
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.capabilities import Capabilities
from app.config import get_settings
from app.core.errors import AppError
from app.db.models import IntakeSession, Turn
from app.graph.resources import Resources
from app.graph.service import IntakeService
from app.integrations.ollama import OllamaClient
from app.llm import LLM
from app.schemas import Extraction, ground
from app.usage import Usage
from scripts.field_recovery import extraction_detail, write_detail
from scripts.normalisation_rescore import OUT, corrected_counts, read_jsonl

CALL_CAP = 102
ATTEMPT_CAP = 150
PREREG = OUT / "field_recovery_run2_preregistration.md"
DETAIL = OUT / "field_recovery_run2_detail.jsonl"
REPORT = OUT / "field_recovery_run2.md"
NORMALISATION_SHA = "8a95b25fbe927ee919df3113bb117c5a699eece4ef97fae57e4ce119a8cc25ee"


class CapReached(Exception):
    pass


class CappedEvaluationLLM(LLM):
    async def _call(
        self, model, msgs, schema, role_cfg, trail, role, attempts, repair, chain_index
    ):
        try:
            return await super()._call(
                model, msgs, schema, role_cfg, trail, role, attempts, repair, chain_index
            )
        except CapReached as exc:
            # The request hook blocked the last entry before transport.
            exc.trail = trail
            exc.attempts = attempts[:-1]
            raise


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan(pairs, clips, items):
    strata = {
        lang: sorted(row["item_id"] for row in pairs if row["lang"] == lang)
        for lang in sorted({row["lang"] for row in pairs})
    }
    quotas = {lang: {"en": 3, "hi": 5, "hinglish": 5}.get(lang, 2) for lang in strata}
    remaining = 30 - sum(quotas.values())
    for lang, ids in strata.items():
        if remaining and len(ids) > quotas[lang]:
            quotas[lang] += 1
            remaining -= 1
    # A stratum with only one completed pair may still have an available reference.
    for lang, ids in strata.items():
        if len(ids) < quotas[lang]:
            additional = sorted(
                row["item_id"]
                for row in items.values()
                if row["lang"] == lang and row["item_id"] not in ids
            )
            strata[lang] = sorted(ids + additional[: quotas[lang] - len(ids)])
    subset = {lang: strata[lang][:count] for lang, count in quotas.items()}
    assert sum(map(len, subset.values())) == 30 and all(
        len(subset[lang]) == count for lang, count in quotas.items()
    )
    saved = {row["item_id"]: row for row in pairs}
    telugu = sorted(
        row["item_id"]
        for row in clips
        if row["lang"] == "te"
        and (
            row["item_id"] not in saved
            or all(
                saved[row["item_id"]][side]["status"] != "ok"
                for side in ("reference", "transcript")
            )
        )
    )
    assert len(telugu) == 6
    return subset, telugu


def preregistration(subset, telugu):
    assert sha(OUT / "normalisation_preregistration.md") == NORMALISATION_SHA
    lines = [
        "# Field recovery run 2 preregistration",
        "",
        "Cap of 102 extraction invocations and 150 Ollama chat attempts. Stop and report before exceeding either cap.",
        "Run three reference-side repetitions on the same 30 items. Each input uses a fresh durable intake session and one turn with production routing, prompts, schema, and grounding.",
        "Within each stratum select sorted item IDs. Quotas start at 3 en, 5 hi, 5 hinglish and 2 per other stratum. Allocate remaining places one at a time in sorted stratum order where capacity permits.",
        "Reference selection uses completed run 1 pairs. Gujarati has one completed pair, so add the first other Gujarati corpus reference in item-ID order to meet its minimum. Punjabi has no completed run 1 pairs.",
        "Run the Telugu items absent on both sides of run 1 in both conditions, once per side.",
        f"The frozen Part 1 rules apply. SHA-256 `{NORMALISATION_SHA}`.",
        "Save the gateway trail and structured attempt metadata for each extraction. Report max minus min recall across repetitions on identical inputs. Compare the magnitude of run 1's English drop with that spread, using all completed English pairs and separately the overlapping subset.",
        "",
        "## Variance subset",
        "",
        *[f"- {lang} · {', '.join(ids)}" for lang, ids in subset.items()],
        "",
        "## Telugu pairs missing on both sides",
        "",
        *[f"- {item_id}" for item_id in telugu],
    ]
    return "\n".join(lines) + "\n"


def totals(item, source, detail):
    original = sum(field["correct"] for field in detail["fields"].values())
    denominator = sum(field["expected"] for field in detail["fields"].values())
    kept, _ = ground(source, Extraction.model_validate(detail["kept_extraction"]))
    corrected = original
    for field in ("age", "language_spoken"):
        label = item["expected"][field]
        if label:
            corrected += (
                corrected_counts(field, label["value"], kept)["correct"]
                - detail["fields"][field]["correct"]
            )
    return original, corrected, denominator


async def execute(items, clips, pairs, subset, telugu):
    cfg = get_settings().model_copy(update={"database_url": os.environ["SPEECH_EVAL_DATABASE_URL"]})
    # Explicitly require a disposable database.
    if not (make_url(cfg.database_url).database or "").endswith("_test"):
        raise ValueError("Use a disposable database ending in _test")
    if not cfg.ollama_key.get_secret_value():
        raise ValueError("Ollama credentials are missing")
    engine = create_async_engine(cfg.database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    redis = FakeRedis()
    client = OllamaClient(cfg.ollama_base, cfg.ollama_key.get_secret_value())
    caps = Capabilities(client, cfg.models())
    usage = Usage(redis, cfg.models())
    llm = CappedEvaluationLLM(client, cfg.models(), capabilities=caps, usage=usage)
    intake = IntakeService(cfg, factory, redis, llm, Resources())
    attempts = calls = 0
    outcomes = Counter()
    attempt_models = Counter()
    rows = []
    stopped = None

    async def count(request):
        nonlocal attempts
        if request.url.path == "/api/chat":
            if attempts >= ATTEMPT_CAP:
                raise CapReached("Ollama attempt cap")
            attempts += 1

    client._c.event_hooks["request"].append(count)

    async def extract(item_id, side, rep, cohort):
        nonlocal calls
        if calls >= CALL_CAP or attempts >= ATTEMPT_CAP:
            raise CapReached("Extraction or Ollama attempt cap")
        item = items[item_id]
        source = item["text"] if side == "reference" else clips[item_id]["transcript"]
        lang = "hi" if item["lang"] == "hinglish" else item["lang"]
        sid = await intake.create("missing", lang, secrets.token_urlsafe(32), None)
        async with factory() as db:
            session = await db.get(IntakeSession, UUID(sid))
        assert session is not None
        calls += 1
        try:
            state = await intake.run_turn(
                session, {"text": source, "mode": "text", "stt_ms": 0, "lang": lang}, "turn:eval"
            )
        except CapReached as exc:
            detail = extraction_detail(
                item, source, "cap_interrupted", None, None, exc.trail, exc.attempts
            )
        except AppError as exc:
            if exc.code != "model_unavailable":
                raise
            # The production node persists the failed trail before raising.
            async with factory() as db:
                failed = await db.scalar(select(Turn).where(Turn.session_id == UUID(sid)))
            assert failed is not None
            trace = failed.models
            detail = extraction_detail(
                item,
                source,
                "model_unavailable",
                trace["turn"],
                None,
                trace["trail"],
                trace["attempts"],
            )
        else:
            extraction = state.get("extraction")
            detail = extraction_detail(
                item,
                source,
                "ok" if extraction else "missing_extraction",
                state.get("model"),
                Extraction.model_validate(extraction) if extraction else None,
                state.get("trail", []),
                state.get("attempts", []),
            )
        outcomes.update(attempt["outcome"] for attempt in detail["attempts"])
        attempt_models.update(attempt["model"] for attempt in detail["attempts"])
        return dict(
            item_id=item_id, lang=item["lang"], side=side, repetition=rep, cohort=cohort, **detail
        )

    try:
        probe = await caps.probe()
        if probe["error"]:
            stopped = "Ollama availability probe failed before extraction"
        else:
            with DETAIL.open("x") as handle:
                for item_id, side, rep, cohort in [
                    (item_id, "reference", rep, "variance")
                    for rep in range(1, 4)
                    for ids in subset.values()
                    for item_id in ids
                ] + [
                    (item_id, side, 1, "telugu")
                    for item_id in telugu
                    for side in ("reference", "transcript")
                ]:
                    row = await extract(item_id, side, rep, cohort)
                    write_detail(handle, row)
                    rows.append(row)
                    if row["status"] == "cap_interrupted":
                        raise CapReached("Ollama attempt cap interrupted an extraction")
                    if calls % 10 == 0:
                        print(f"{calls} extractions, {attempts} Ollama chat attempts", flush=True)
    except CapReached as exc:
        stopped = str(exc)
    except Exception as exc:
        stopped = f"Execution stopped with {type(exc).__name__}"
    finally:
        await intake.close()
        await client.aclose()
        await redis.aclose()
        await engine.dispose()
    report(
        items,
        clips,
        pairs,
        subset,
        telugu,
        rows,
        calls,
        attempts,
        outcomes,
        attempt_models,
        stopped,
    )


def report(items, clips, pairs, subset, telugu, rows, calls, attempts, outcomes, models, stopped):
    lines = [
        "# Field recovery run 2",
        "",
        f"Preregistration SHA-256 `{sha(PREREG)}`.",
        f"Extraction invocations {calls}/{CALL_CAP}. Ollama chat attempts {attempts}/{ATTEMPT_CAP}. Gnani requests 0.",
        f"Saved extraction results {len(rows)}. Logged attempts {sum(outcomes.values())}.",
        "Planned execution uses the production intake graph with disposable PostgreSQL and an isolated Redis emulator for the usage ledger. The text-only path bypasses speech delivery.",
        *[f"- Attempt outcome {outcome} · {count}" for outcome, count in sorted(outcomes.items())],
        *[f"- Attempt model {model} · {count}" for model, count in sorted(models.items())],
    ]
    if stopped:
        lines.extend(["", f"Stop reason · {stopped}."])
    lines.extend(["", "## Reference variance", ""])
    spreads = {}
    for lang in ["overall", *subset]:
        groups = [
            [
                row
                for row in rows
                if row["cohort"] == "variance"
                and row["side"] == "reference"
                and row["repetition"] == rep
                and row["item_id"]
                in (set(sum(subset.values(), [])) if lang == "overall" else subset[lang])
            ]
            for rep in range(1, 4)
        ]
        planned = sum(map(len, subset.values())) if lang == "overall" else len(subset[lang])
        for version, i in (("original", 0), ("corrected", 1)):
            recalls = []
            for group in groups:
                scores = [
                    totals(items[row["item_id"]], items[row["item_id"]]["text"], row)
                    for row in group
                ]
                denom = sum(score[2] for score in scores)
                recalls.append(
                    sum(score[i] for score in scores) / denom
                    if denom and len(group) == planned
                    else None
                )
            spread = max(recalls) - min(recalls) if None not in recalls else None
            spreads[lang, version] = spread
            values = ", ".join(
                "unavailable" if value is None else f"{value:.2%}" for value in recalls
            )
            text = "unavailable" if spread is None else f"{spread * 100:.2f} pp"
            lines.append(
                f"- {lang}, {version}, n={planned} per repetition · {values} · spread {text}"
            )
    lines.extend(["", "## Telugu", ""])
    for item_id in telugu:
        for side in ("reference", "transcript"):
            selected = [
                row
                for row in rows
                if row["item_id"] == item_id and row["side"] == side and row["cohort"] == "telugu"
            ]
            if selected:
                row = selected[-1]
                source = (
                    items[item_id]["text"] if side == "reference" else clips[item_id]["transcript"]
                )
                original, corrected, denom = totals(items[item_id], source, row)
                lines.append(
                    f"- {item_id}, {side} · {row['status']} · original {original}/{denom}, corrected {corrected}/{denom}."
                )
            else:
                lines.append(f"- {item_id}, {side} · unavailable.")
    lines.extend(["", "## English run 1 comparison", ""])
    for name, english in (
        ("all English", [row for row in pairs if row["lang"] == "en"]),
        ("variance subset", [row for row in pairs if row["item_id"] in subset["en"]]),
    ):
        scores = {side: [] for side in ("reference", "transcript")}
        for pair in english:
            item_id = pair["item_id"]
            for side, source in (
                ("reference", items[item_id]["text"]),
                ("transcript", clips[item_id]["transcript"]),
            ):
                scores[side].append(totals(items[item_id], source, pair[side]))
        for version, i in (("original", 0), ("corrected", 1)):
            a, b = [
                sum(row[i] for row in scores[side]) / sum(row[2] for row in scores[side])
                for side in scores
            ]
            spread = spreads["en", version]
            verdict = (
                "unavailable" if spread is None else "inside" if abs(b - a) <= spread else "outside"
            )
            lines.append(
                f"- {name}, {version}, n={len(english)} · {a:.2%} to {b:.2%}, {(b - a) * 100:+.2f} pp · variance comparison {verdict}."
            )
    REPORT.write_text("\n".join(lines) + "\n")
    print(
        f"Run 2 stopped: {stopped or 'complete'}; {calls} extractions, {attempts} Ollama chat attempts, 0 Gnani requests.",
        flush=True,
    )


def main():
    logging.disable(logging.CRITICAL)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--preregister", action="store_true")
    parser.add_argument("--sha")
    args = parser.parse_args()
    pairs = read_jsonl(OUT / "field_recovery_detail.jsonl")
    clips = read_jsonl(OUT / "transcripts.jsonl")
    items = {item["item_id"]: item for item in read_jsonl(args.items)}
    subset, telugu = plan(pairs, clips, items)
    registration = preregistration(subset, telugu)
    if args.preregister:
        with PREREG.open("x") as handle:
            handle.write(registration)
        print(f"Run 2 preregistration SHA-256 {sha(PREREG)}")
        return
    if PREREG.read_text() != registration or args.sha != sha(PREREG) or DETAIL.exists():
        parser.error("Run requires matching preregistration hash and a new detail file")
    asyncio.run(execute(items, {row["item_id"]: row for row in clips}, pairs, subset, telugu))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Run 2 preflight stopped with {type(exc).__name__}") from None
