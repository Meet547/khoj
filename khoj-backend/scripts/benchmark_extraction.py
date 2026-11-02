#!/usr/bin/env python3
"""Paired live extraction trials, including safe per-attempt diagnostics (no thinking text)."""

import argparse
import asyncio
import copy
import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.api.gateway import EXTRACT_PROMPT  # noqa: E402
from app.config import Settings  # noqa: E402
from app.graph.resources import Resources  # noqa: E402
from app.integrations.ollama import OllamaClient  # noqa: E402
from app.llm import LLM  # noqa: E402
from app.schemas import Extraction, ground  # noqa: E402
from scripts.extraction_metrics import breakdown, score  # noqa: E402


class ObservedClient(OllamaClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.observed = []

    async def chat(self, model, messages, **kwargs):
        attempt = {
            "attempt": len(self.observed) + 1,
            "model": model,
            "think": kwargs.get("think"),
            "phase": "repair"
            if messages[-1]["content"]
            == "That was not valid JSON for the schema. Reply with only the JSON."
            else "initial",
        }
        self.observed.append(attempt)
        start = time.perf_counter()
        try:
            data = await super().chat(model, messages, **kwargs)
            attempt["outcome"] = "response"
            try:
                Extraction.model_validate_json((data.get("message") or {}).get("content", ""))
            except Exception:
                attempt["outcome"] = "invalid_json"
            attempt["thinking_present"] = bool((data.get("message") or {}).get("thinking"))
            for key in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration"):
                if key in data:
                    attempt[key + "_ms"] = round(data[key] / 1_000_000, 3)
            for key in ("prompt_eval_count", "eval_count"):
                if key in data:
                    attempt[key] = data[key]
            return data
        except BaseException as exc:
            attempt["outcome"] = (
                "cancelled_or_timeout"
                if isinstance(exc, asyncio.CancelledError)
                else type(exc).__name__
            )
            if hasattr(exc, "status"):
                attempt["status"] = exc.status
            raise
        finally:
            attempt["wall_ms"] = round((time.perf_counter() - start) * 1000, 3)


def percentiles(values):
    if not values:
        return None
    ordered = sorted(values)
    return {
        "n": len(values),
        "p50_ms": statistics.median(ordered),
        "p95_ms": ordered[math.ceil(0.95 * len(ordered)) - 1],
        "max_ms": max(ordered),
    }


def baseline_class(path):
    spec = importlib.util.spec_from_file_location("app._followup_baseline", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.LLM


async def benchmark(args):
    settings = Settings(env="test", _env_file=ROOT / ".env")
    resources = Resources()
    rows = [
        json.loads(line)
        for line in (await asyncio.to_thread(args.dataset.read_text)).splitlines()
        if line.strip()
    ]
    if args.gateway_input:
        row = {
            "id": "historical-smoke-input",
            "lang": "hi",
            "category": "clean",
            "transcript": "यह काल्पनिक विवरण है, राहुल 24 साल का है और हिंदी बोलता है।",
            "expected_fields": [
                dict(name="name", value="Rahul", evidence="राहुल"),
                dict(name="age", value="24", evidence="24 साल"),
                dict(name="language", value="Hindi", evidence="हिंदी बोलता है"),
            ],
        }
        rows = [{**row, "id": f"gateway-{i + 1:02}"} for i in range(args.trials)]
    else:
        if len(rows) < args.trials:
            raise ValueError("Not enough fixed inputs for the requested trials")
        rows = rows[: args.trials]
    cfg = yaml.safe_load(args.config.read_text()) if args.config else settings.models()
    cls = baseline_class(args.baseline_llm) if args.baseline_llm else LLM
    client = ObservedClient(settings.ollama_base, settings.ollama_key.get_secret_value())
    arms = args.arms.split(",")
    records = []
    rng = random.Random(args.seed)
    # Record actual endpoint metadata, not assumptions from model names.
    show = await client._c.post("/api/show", json={"model": "gemma4:31b"})
    metadata = {
        "status": show.status_code,
        "thinking": show.json().get("thinking") if show.status_code == 200 else None,
    }
    try:
        for index, row in enumerate(rows):
            order = arms.copy()
            rng.shuffle(order)
            for arm in order:
                config = copy.deepcopy(cfg)
                if arm in {"false", "true"}:
                    config["roles"]["turn"]["primary"] = "gemma4:31b"
                    config["roles"]["turn"]["fallback"] = []
                    config["roles"]["turn"]["think"] = arm == "true"
                    config["roles"]["turn"]["think_by_model"] = {}
                    config["language_overrides"] = {}
                if args.attempt_timeout is not None:
                    config["attempt_timeout_seconds"] = args.attempt_timeout
                gateway = cls(client, config)
                client.observed = []
                start = time.perf_counter()
                failure = None
                result = None
                try:
                    messages = (
                        resources.messages(row["transcript"], {}, None)
                        if not args.gateway_input
                        else [
                            {"role": "system", "content": EXTRACT_PROMPT},
                            {"role": "user", "content": row["transcript"]},
                        ]
                    )
                    result = await gateway.run(
                        "turn",
                        messages,
                        schema_model=Extraction,
                        lang="hi" if row["lang"] == "hinglish" else row["lang"],
                    )
                except Exception as exc:
                    failure = type(exc).__name__
                wall = round((time.perf_counter() - start) * 1000, 3)
                raw = result.parsed.fields if result and result.parsed else []
                kept, _ = (
                    ground(row["transcript"], result.parsed)
                    if result and result.parsed
                    else ([], [])
                )
                record = {
                    **score(
                        row, [f.model_dump() for f in raw], [f.model_dump() for f in kept], failure
                    ),
                    "arm": arm,
                    "trial": index + 1,
                    "wall_ms": wall,
                    "model": result.model if result else None,
                    "trail": result.trail if result else [],
                    "attempts": copy.deepcopy(client.observed),
                    "gateway_attempts": getattr(result, "attempts", []) if result else [],
                }
                records.append(record)
                print(
                    json.dumps(
                        {
                            "trial": index + 1,
                            "arm": arm,
                            "case": row["id"],
                            "wall_ms": wall,
                            "failure": failure,
                            "attempts": len(client.observed),
                        }
                    ),
                    flush=True,
                )
                await write_report(args, records, metadata, resources, rows)
    finally:
        await client.aclose()
    return await write_report(args, records, metadata, resources, rows)


async def write_report(args, records, metadata, resources, rows):
    grouped = {}
    for arm in args.arms.split(","):
        selected = [r for r in records if r["arm"] == arm]
        grouped[arm] = {
            "latency_all": percentiles([r["wall_ms"] for r in selected]),
            "latency_successful": percentiles([r["wall_ms"] for r in selected if not r["failure"]]),
            **breakdown(selected),
        }
    report = {
        "mode": "live",
        "prompt_hash": resources.hashes["turn-analysis"],
        "input_hash": hashlib.sha256(
            json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "paired": len(args.arms.split(",")) > 1,
        "seed": args.seed,
        "attempt_timeout_override": args.attempt_timeout,
        "gateway_input": args.gateway_input,
        "gemma_show": metadata,
        "summary": grouped,
        "records": records,
    }
    await asyncio.to_thread(args.output.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(
        args.output.write_text, json.dumps(report, ensure_ascii=False, indent=2)
    )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, default=ROOT / "evals/extraction/benchmark.v1.jsonl")
    p.add_argument("--trials", type=int, default=20)
    p.add_argument("--arms", default="false,true")
    p.add_argument("--seed", type=int, default=20261102)
    p.add_argument("--gateway-input", action="store_true")
    p.add_argument("--baseline-llm", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--attempt-timeout", type=float)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    asyncio.run(benchmark(args))


if __name__ == "__main__":
    main()
