#!/usr/bin/env python3
"""Assemble before/after evidence without invoking models or changing frozen labels."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.extraction_metrics import breakdown, counts  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/b2-followup"
DATA = ROOT / "khoj-backend/evals/extraction"


def read(name):
    return json.loads((OUTPUT / name).read_text())


def slow_runs(experiment, rows):
    result = []
    for row in rows:
        wall = row.get("wall_ms", row.get("latency_ms"))
        if wall is None or wall < 2000:
            continue
        attempts = (
            row.get("gateway_attempts") or row.get("attempts") or row.get("observed_attempts") or []
        )
        flags = []
        if any(a.get("phase") == "repair" or a.get("outcome") == "invalid_json" for a in attempts):
            flags.append("json_repair")
        if any(a.get("status") == 429 for a in attempts):
            flags.append("429_retry")
        if any(a.get("outcome") in {"timeout", "cancelled_or_timeout"} for a in attempts):
            flags.append("timeout")
        if len({a["model"] for a in attempts}) > 1 or any(a.get("fallback") for a in attempts):
            flags.append("model_fallback")
        if not flags:
            flags = ["single_initial_request"]
        result.append(
            {
                "experiment": experiment,
                "case": row["case"],
                "trial": row.get("trial"),
                "arm": row.get("arm"),
                "wall_ms": wall,
                "classification": flags,
                "attempts": attempts,
                "generation_attribution": "Separate generation/queue timings unavailable when only total_duration is returned; wall minus server total also includes network/client overhead.",
            }
        )
    return result


def short(metrics):
    if metrics is None:
        return "N/A"
    f = "N/A" if metrics["f1"] is None else f"{metrics['f1']:.3f}"
    return f"F1 {f}, strict hallucination count {metrics['hallucination_count']} (n={metrics['cases']})"


def main():
    original = [json.loads(line) for line in (DATA / "cases.v1.jsonl").read_text().splitlines()]
    dev = [json.loads(line) for line in (DATA / "development.v2.jsonl").read_text().splitlines()]
    held = [json.loads(line) for line in (DATA / "heldout.v1.jsonl").read_text().splitlines()]
    before_dev = read("development-before.json")
    before_held = read("heldout-before.json")
    after = read("quality-after.json")
    before = {
        key: breakdown(r["records"]["chain"])
        for key, r in [("development", before_dev), ("heldout", before_held)]
    }
    after_metrics = {
        split: breakdown([r for r in after["records"]["chain"] if r["split"] == split])
        for split in ("development", "heldout")
    }
    old = read("baseline/latency-live-20.json")
    replay = read("baseline-gateway-replay-20.json")
    policy = read("gateway-after-20.json")
    paired = read("think-paired-20.json")
    old_lat = old["percentiles"]["turn_ms"]
    before_lat = replay["summary"]["legacy"]["latency_all"]
    after_lat = policy["summary"]["policy"]["latency_all"]
    assert replay["input_hash"] == policy["input_hash"]
    slow = []
    for index, row in enumerate(old["measurements"], 1):
        if row["turn_ms"] >= 2000:
            slow.append(
                {
                    "experiment": "historical_http_smoke",
                    "trial": index,
                    "wall_ms": row["turn_ms"],
                    "model": None,
                    "attempt": None,
                    "classification": ["unrecoverable_missing_attempt_traces"],
                    "reason": "The historical file retained only stage latencies. /api/llm/turn did not persist turns. Top-level model describes the final trial, not every trial.",
                }
            )
    for name, rows in [
        ("frozen_gateway_replay", replay["records"]),
        ("thinking_AB", paired["records"]),
        ("development_before", before_dev["records"]["chain"]),
        ("heldout_before", before_held["records"]["chain"]),
        ("quality_after", after["records"]["chain"]),
        ("gateway_after", policy["records"]),
    ]:
        slow.extend(slow_runs(name, rows))
    frozen = json.loads((OUTPUT / "baseline/frozen-hashes.json").read_text())
    unchanged = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        for name, digest in frozen.items()
        if "/graph/prompts/" in name or name.endswith("/schemas.py")
    }
    assert all(unchanged.values())
    report = {
        "coverage": {
            "original_30": counts(original),
            "development_37": counts(dev),
            "heldout_35": counts(held),
        },
        "quality": {"before": before, "after": after_metrics},
        "historical_http_latency": old["percentiles"]["turn_ms"],
        "same_input_replay": {
            "before": replay["summary"]["legacy"],
            "after": policy["summary"]["policy"],
            "input_hash_equal": True,
            "scope": "Direct extraction core, same original Hindi input; excludes HTTP/Redis budget overhead. Separate time windows, not causal proof of improvement.",
        },
        "thinking_AB": paired["summary"],
        "thinking_metadata": paired["gemma_show"],
        "thinking_comparison_timeout_seconds": paired["attempt_timeout_override"],
        "slow_runs": slow,
        "frozen_files_unchanged": unchanged,
        "heldout_mismatch_review": [
            {
                "case": "heldout-11",
                "type": "location_specificity_loss",
                "expected": "outside Panvel station",
                "kept": "Panvel station",
            },
            {
                "case": "heldout-14",
                "type": "equivalent_article_wording",
                "expected": "scar above left eyebrow",
                "kept": "scar above the left eyebrow",
            },
            {
                "case": "heldout-27",
                "type": "equivalent_translation_wording",
                "expected": "white scarf",
                "kept": "white dupatta",
            },
        ],
        "limitations": [
            "Strict hallucination metric counts unexpected field/value pairs, including unannotated paraphrases; all mismatches retain evidence for review.",
            "Heldout labels and prompts were not changed after observation. The real zero-FP gate remains failed at 3 strict mismatches.",
            "20 trials per arm have noisy tails; maxima and every slow run are retained. Old missing trails cannot be reconstructed.",
            "6 seconds is per attempt, not an end-to-end chain deadline.",
        ],
    }
    (OUTPUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (OUTPUT / "slow-runs.json").write_text(json.dumps(slow, ensure_ascii=False, indent=2))
    labels = {
        "clean_single_language": "Clean single-language",
        "hinglish": "Hinglish (cross-cutting)",
        "long_rambling": "Long/rambling",
        "corrections": "Corrections",
        "conflicting_values": "Conflicting values",
        "stt_errors": "STT-style errors",
        "injection_attempts": "Injection attempts",
    }
    lines = [
        "# B2 follow-up: frozen evaluation and tail diagnostics",
        "",
        "Measured 2 November 2026 against real Ollama Cloud. Prompts and Extraction schemas are byte-for-byte unchanged. The original 30 cases remain unchanged.",
        "",
        "## Coverage and hold-out protocol",
        "",
        "Counts below are original 30 → expanded development 37 / new held-out 35. Hinglish overlaps the difficulty categories; counts are not additive. The 35 held-out texts and labels were written and hashed before provider runs. No held-out-driven prompt, configuration, alias or label tuning was performed. Configuration was selected from the separate development benchmark.",
        "",
    ]
    for key in labels:
        lines.append(
            f"- {labels[key]}: {counts(original)[key]} → {counts(dev)[key]} / {counts(held)[key]}."
        )
    lines += [
        "",
        "## Quality before and after",
        "",
        "Original seed report: F1 1.0 and zero scored false positives on 30 previously tuned examples. The expanded development and held-out sets were each measured with the frozen old gateway and the final gateway.",
        "",
        f"- Development before: {short(before['development']['overall'])}; after: {short(after_metrics['development']['overall'])}.",
        f"- Held-out before: {short(before['heldout']['overall'])}; after: {short(after_metrics['heldout']['overall'])}.",
        "",
        "Per-category entries show development before → after; then held-out before → after. F1 is N/A for a category with no positive field labels and no predictions; correct abstentions are reported instead.",
        "",
    ]
    for key, label in labels.items():
        b = before["development"]["by_category"][key]
        a = after_metrics["development"]["by_category"][key]
        h = before["heldout"]["by_category"][key]
        ha = after_metrics["heldout"]["by_category"][key]
        lines.append(f"- {label}: dev {short(b)} → {short(a)}; held-out {short(h)} → {short(ha)}.")
    lines += ["", "Per-language entries (development before → after; held-out before → after):", ""]
    for lang in ("en", "hi", "hinglish", "mr"):
        lines.append(
            f"- {lang}: dev {short(before['development']['by_language'][lang])} → {short(after_metrics['development']['by_language'][lang])}; held-out {short(before['heldout']['by_language'][lang])} → {short(after_metrics['heldout']['by_language'][lang])}."
        )
    lines += [
        "",
        "All five conflicting-value and all five injection held-out cases correctly abstained, before and after. `report.json` also contains every category × language cross-tab.",
        "",
        "The three strict-label mismatches are preserved, not relabelled to obtain a pass:",
        "- heldout-11: expected “outside Panvel station”; kept “Panvel station” (lost spatial qualifier).",
        "- heldout-14: expected “scar above left eyebrow”; kept “scar above the left eyebrow” (equivalent wording).",
        "- heldout-27: expected “white scarf”; kept “white dupatta” (equivalent translation).",
        "",
        "These three scored field mismatches are not three invented facts. The strict zero-FP live gate remains failed. No prompt or label was changed to remove them.",
        "",
        "## Thinking controls and paired experiment",
        "",
        'Live `/api/show`: Gemma `thinking.values=[false,true]`, `default=false`; GPT-OSS values are `low`, `medium`, `high`. Gemma `think:"low"` is unsupported; observed legacy replays produced no thinking. The final router sends explicit `false` to Gemma and preserves valid GPT-OSS levels. See [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking) and [Gemma renderer](https://github.com/ollama/ollama/blob/main/model/renderers/gemma4.go).',
        "",
        "Twenty identical paired development inputs per arm, deterministic randomized interleaving (seed 20261102), Gemma only. An explicit 90-second experimental ceiling avoids censoring the thinking-quality comparison; production remains 6 seconds per attempt. No prompts, schemas or labels varied between arms.",
        "",
    ]
    for arm, label in [("false", "Thinking disabled"), ("true", "Thinking enabled")]:
        s = paired["summary"][arm]
        lat = s["latency_all"]
        lines.append(
            f"- {label}: n={lat['n']}, p50 {lat['p50_ms']:.1f} ms, p95 {lat['p95_ms']:.1f} ms, max {lat['max_ms']:.1f} ms; {short(s['overall'])}."
        )
    lines += [
        "",
        "Thinking was present in 20/20 enabled responses and 0/20 disabled responses. No chain-of-thought text was saved.",
        "",
        "## Tail timing before and after",
        "",
        f"- Original HTTP smoke: p50 {old_lat['p50']} ms, p95 {old_lat['p95']} ms, max {max(row['turn_ms'] for row in old['measurements'])} ms. p95 nearest-rank excludes the single worst of 20 samples.",
        f"- Frozen old extraction-core replay: p50 {before_lat['p50_ms']:.1f} ms, p95 {before_lat['p95_ms']:.1f} ms, max {before_lat['max_ms']:.1f} ms.",
        f"- Final extraction-core replay: p50 {after_lat['p50_ms']:.1f} ms, p95 {after_lat['p95_ms']:.1f} ms, max {after_lat['max_ms']:.1f} ms; {short(policy['summary']['policy']['overall'])}.",
        "",
        f"The new replay's p95 is {'higher' if after_lat['p95_ms'] > before_lat['p95_ms'] else 'lower'} than the frozen replay. These sequential samples do not establish a causal latency improvement. Cloud/provider and client timing varied. The timeout behavior is verified directly, not inferred from p95.",
        "",
        "Historical slow runs (≥2000 ms) have no stored attempt traces:",
        "- Trial 4: 2522 ms — model/attempt/cause unavailable.",
        "- Trial 9: 4491 ms — model/attempt/cause unavailable.",
        "- Trial 11: 19026 ms — model/attempt/cause unavailable.",
        "- Trial 16: 2092 ms — model/attempt/cause unavailable.",
        "",
        "The old artifact saved only stage latencies. Its top-level model is the final trial model. The stateless route did not write these requests into `turns`, so attributing those historical delays to repair, fallback, 429 or generation would be fabrication.",
        "",
        "Every newly observed slow run is listed below and in `slow-runs.json`. Separate generation/queue durations were not returned by Cloud; “single initial request” does not prove compute-only generation delay. Server `total_duration` and request wall time are retained.",
        "",
    ]
    for row in slow:
        if "attempts" not in row:
            continue
        desc = []
        for a in row["attempts"]:
            server = (
                f", server total {a['total_duration_ms']:.1f} ms"
                if "total_duration_ms" in a
                else ""
            )
            desc.append(
                f"attempt {a['attempt']} {a['model']} {a['phase']}/{a['outcome']} {a['wall_ms']:.1f} ms{server}"
            )
        suffix = f" trial {row['trial']}" if row.get("trial") else ""
        lines.append(
            f"- {row['experiment']}{suffix} {row.get('arm') or ''} {row['case']}: {row['wall_ms']:.1f} ms; {', '.join(row['classification'])}; "
            + "; ".join(desc)
            + "."
        )
    lines += [
        "",
        "The final trial 6 demonstrates a 6001.5 ms Gemma timeout followed by a successful 2604.4 ms GPT-OSS attempt, totaling 8607.5 ms. Timeouts skip that model, without a same-model transport retry. JSON repair and HTTP 429 retry remain separately labelled/tested.",
        "",
        "## Reproduction",
        "",
        "From `khoj-backend`:",
        "",
        "```sh",
        ".venv/bin/python scripts/eval_extraction.py --heldout evals/extraction/heldout.v1.jsonl --output ../artifacts/b2-followup/quality-after.json",
        ".venv/bin/python scripts/benchmark_extraction.py --arms false,true --attempt-timeout 90 --output ../artifacts/b2-followup/think-paired-20.json",
        ".venv/bin/python scripts/benchmark_extraction.py --gateway-input --arms policy --output ../artifacts/b2-followup/gateway-after-20.json",
        ".venv/bin/python -m scripts.report_extraction_followup",
        "```",
        "",
        "Live evaluation exits nonzero for any strict false positive or provider failure. Fake CI checks the harness with an intentionally ungrounded extra field; it does not establish model quality. `models.yaml` configures `attempt_timeout_seconds: 6`. Future smoke reports and `turns.models.attempts` store per-attempt model, phase, retry, timeout, wall/server timing and outcome, including exhausted analyses.",
    ]
    (OUTPUT / "README.md").write_text("\n".join(lines) + "\n")
    print("Wrote report.json, slow-runs.json and README.md")


if __name__ == "__main__":
    main()
