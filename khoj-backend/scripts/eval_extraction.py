#!/usr/bin/env python3
"""Frozen-label extraction metrics by category, language and development/held-out split.

--fake checks the metric/grounding harness; real runs measure the actual model chain.
No report tunes prompts or rewrites annotations. Every attempt is retained, without thinking text.
"""

import argparse
import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import Settings  # noqa: E402
from app.graph.resources import Resources  # noqa: E402
from app.llm import LLM  # noqa: E402
from app.schemas import Extraction, ground  # noqa: E402
from scripts.benchmark_extraction import ObservedClient, baseline_class  # noqa: E402
from scripts.extraction_metrics import breakdown, counts, norm, pairs, score  # noqa: E402,F401 -- retained public helpers


async def evaluate(
    dataset, models, output, fake=False, *, heldout=None, baseline_llm=None, config_path=None
):
    settings = Settings(env="test", _env_file=ROOT / ".env")
    resources = Resources()
    paths = [dataset] + ([heldout] if heldout else [])
    cases = [
        json.loads(line) for path in paths for line in path.read_text().splitlines() if line.strip()
    ]
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    reports = {}
    results = {}
    all_records = {}
    for model in models:
        lookup = {row["transcript"]: row for row in cases}

        def handler(req, lookup=lookup):
            import html
            import re

            body = json.loads(req.content)
            text = html.unescape(
                re.sub(
                    r"^<user_message>|</user_message>$",
                    "",
                    [m["content"] for m in body["messages"] if m["role"] == "user"][-1],
                )
            )
            row = lookup[text]
            fields = [
                *row["expected_fields"],
                {
                    "name": "hair",
                    "value": "invented purple hair",
                    "evidence": "never said by this person",
                },
            ]
            return httpx.Response(
                200,
                json={
                    "message": {"content": json.dumps({"intent": row["intent"], "fields": fields})}
                },
            )

        client = ObservedClient(
            settings.ollama_base,
            settings.ollama_key.get_secret_value(),
            transport=httpx.MockTransport(handler) if fake else None,
        )
        cfg = copy.deepcopy(
            yaml.safe_load(config_path.read_text()) if config_path else settings.models()
        )
        if model != "chain":
            cfg["roles"]["turn"]["primary"] = model
            cfg["roles"]["turn"]["fallback"] = []
            cfg["language_overrides"] = {}
        cls = baseline_class(baseline_llm) if baseline_llm else LLM
        llm = cls(client, cfg)
        records = []
        chains = {}
        try:
            for index, row in enumerate(cases):
                language = "hi" if row["lang"] == "hinglish" else row["lang"]
                chains[row["lang"]] = llm.chain("turn", language)
                result = None
                failure = None
                failed_attempts = []
                failed_trail = []
                client.observed = []
                try:
                    result = await llm.run(
                        "turn",
                        resources.messages(row["transcript"], {}, None),
                        schema_model=Extraction,
                        lang=language,
                    )
                except Exception as exc:
                    failure = type(exc).__name__
                    failed_attempts = getattr(exc, "attempts", [])
                    failed_trail = getattr(exc, "trail", [])
                extraction = result.parsed if result else None
                raw = extraction.fields if extraction else []
                kept, dropped = ground(row["transcript"], extraction) if extraction else ([], [])
                record = {
                    **score(
                        row, [f.model_dump() for f in raw], [f.model_dump() for f in kept], failure
                    ),
                    "model": result.model if result else None,
                    "chain": chains[row["lang"]],
                    "latency_ms": result.latency_ms if result else None,
                    "trail": result.trail if result else failed_trail,
                    "attempts": getattr(result, "attempts", []) if result else failed_attempts,
                    "observed_attempts": copy.deepcopy(client.observed),
                    "ungrounded_count": len(dropped),
                }
                records.append(record)
                if not fake:
                    print(
                        json.dumps(
                            {
                                "case": row["id"],
                                "split": record["split"],
                                "model": model,
                                "progress": f"{index + 1}/{len(cases)}",
                                "fp": record["fp"],
                                "fn": record["fn"],
                                "failure": failure,
                            }
                        ),
                        flush=True,
                    )
            report = breakdown(records)
            report["by_split"] = {
                split: breakdown([r for r in records if r["split"] == split])
                for split in sorted({r["split"] for r in records})
            }
            reports[model] = report
            all_records[model] = records
            # Preserve the original results[model][language] shape for existing consumers.
            results[model] = {
                lang: {
                    **metrics,
                    "chain": chains[lang],
                    "mismatches": [
                        r
                        for r in records
                        if r["lang"] == lang and (r["fp"] or r["fn"] or r["failure"])
                    ],
                }
                for lang, metrics in report["by_language"].items()
            }
        finally:
            await client.aclose()
    report = {
        "mode": "fake_harness" if fake else "live",
        "dataset": dataset.name,
        "dataset_hash": hashes[dataset.name],
        "dataset_hashes": hashes,
        "prompt_hash": resources.hashes["turn-analysis"],
        "coverage": {
            "all": counts(cases),
            "by_split": {
                split: counts([r for r in cases if r.get("split", "legacy_development") == split])
                for split in sorted({r.get("split", "legacy_development") for r in cases})
            },
        },
        "results": results,
        "breakdowns": reports,
        "records": all_records,
        "passed": all(
            not r["fp"] and not r["failure"] for records in all_records.values() for r in records
        ),
        "metric_definition": "Kept hallucinations = unexpected or incorrectly valued field pairs under frozen exact/annotated-alias labels. F1=null when TP+FP+FN=0; abstention counts are reported. Hinglish is a cross-cutting category.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        json.dumps(
            {"passed": report["passed"], "coverage": report["coverage"], "summary": reports},
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fake", action="store_true")
    p.add_argument("--dataset", type=Path, default=ROOT / "evals/extraction/development.v2.jsonl")
    p.add_argument("--heldout", type=Path)
    p.add_argument("--models", default="chain")
    p.add_argument("--baseline-llm", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--output", type=Path, default=ROOT / "evals/extraction/report.json")
    args = p.parse_args()
    report = asyncio.run(
        evaluate(
            args.dataset,
            args.models.split(","),
            args.output,
            args.fake,
            heldout=args.heldout,
            baseline_llm=args.baseline_llm,
            config_path=args.config,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
