# B2 follow-up: frozen evaluation and tail diagnostics

Measured 2 November 2026 against real Ollama Cloud. Prompts and Extraction schemas are byte-for-byte unchanged. The original 30 cases remain unchanged.

## Coverage and hold-out protocol

Counts below are original 30 → expanded development 37 / new held-out 35. Hinglish overlaps the difficulty categories; counts are not additive. The 35 held-out texts and labels were written and hashed before provider runs. No held-out-driven prompt, configuration, alias or label tuning was performed. Configuration was selected from the separate development benchmark.

- Clean single-language: 4 → 5 / 5.
- Hinglish (cross-cutting): 8 → 9 / 9.
- Long/rambling: 4 → 5 / 5.
- Corrections: 4 → 5 / 5.
- Conflicting values: 3 → 5 / 5.
- STT-style errors: 4 → 5 / 5.
- Injection attempts: 4 → 5 / 5.

## Quality before and after

Original seed report: F1 1.0 and zero scored false positives on 30 previously tuned examples. The expanded development and held-out sets were each measured with the frozen old gateway and the final gateway.

- Development before: F1 1.000, strict hallucination count 0 (n=37); after: F1 1.000, strict hallucination count 0 (n=37).
- Held-out before: F1 0.927, strict hallucination count 3 (n=35); after: F1 0.927, strict hallucination count 3 (n=35).

Per-category entries show development before → after; then held-out before → after. F1 is N/A for a category with no positive field labels and no predictions; correct abstentions are reported instead.

- Clean single-language: dev F1 1.000, strict hallucination count 0 (n=5) → F1 1.000, strict hallucination count 0 (n=5); held-out F1 1.000, strict hallucination count 0 (n=5) → F1 1.000, strict hallucination count 0 (n=5).
- Hinglish (cross-cutting): dev F1 1.000, strict hallucination count 0 (n=9) → F1 1.000, strict hallucination count 0 (n=9); held-out F1 1.000, strict hallucination count 0 (n=9) → F1 1.000, strict hallucination count 0 (n=9).
- Long/rambling: dev F1 1.000, strict hallucination count 0 (n=5) → F1 1.000, strict hallucination count 0 (n=5); held-out F1 0.833, strict hallucination count 2 (n=5) → F1 0.833, strict hallucination count 2 (n=5).
- Corrections: dev F1 1.000, strict hallucination count 0 (n=5) → F1 1.000, strict hallucination count 0 (n=5); held-out F1 1.000, strict hallucination count 0 (n=5) → F1 1.000, strict hallucination count 0 (n=5).
- Conflicting values: dev F1 N/A, strict hallucination count 0 (n=5) → F1 N/A, strict hallucination count 0 (n=5); held-out F1 N/A, strict hallucination count 0 (n=5) → F1 N/A, strict hallucination count 0 (n=5).
- STT-style errors: dev F1 1.000, strict hallucination count 0 (n=5) → F1 1.000, strict hallucination count 0 (n=5); held-out F1 0.800, strict hallucination count 1 (n=5) → F1 0.800, strict hallucination count 1 (n=5).
- Injection attempts: dev F1 N/A, strict hallucination count 0 (n=5) → F1 N/A, strict hallucination count 0 (n=5); held-out F1 N/A, strict hallucination count 0 (n=5) → F1 N/A, strict hallucination count 0 (n=5).

Per-language entries (development before → after; held-out before → after):

- en: dev F1 1.000, strict hallucination count 0 (n=11) → F1 1.000, strict hallucination count 0 (n=11); held-out F1 0.857, strict hallucination count 2 (n=12) → F1 0.857, strict hallucination count 2 (n=12).
- hi: dev F1 1.000, strict hallucination count 0 (n=10) → F1 1.000, strict hallucination count 0 (n=10); held-out F1 0.889, strict hallucination count 1 (n=8) → F1 0.889, strict hallucination count 1 (n=8).
- hinglish: dev F1 1.000, strict hallucination count 0 (n=9) → F1 1.000, strict hallucination count 0 (n=9); held-out F1 1.000, strict hallucination count 0 (n=9) → F1 1.000, strict hallucination count 0 (n=9).
- mr: dev F1 1.000, strict hallucination count 0 (n=7) → F1 1.000, strict hallucination count 0 (n=7); held-out F1 1.000, strict hallucination count 0 (n=6) → F1 1.000, strict hallucination count 0 (n=6).

All five conflicting-value and all five injection held-out cases correctly abstained, before and after. `report.json` also contains every category × language cross-tab.

The three strict-label mismatches are preserved, not relabelled to obtain a pass:
- heldout-11: expected “outside Panvel station”; kept “Panvel station” (lost spatial qualifier).
- heldout-14: expected “scar above left eyebrow”; kept “scar above the left eyebrow” (equivalent wording).
- heldout-27: expected “white scarf”; kept “white dupatta” (equivalent translation).

These three scored field mismatches are not three invented facts. The strict zero-FP live gate remains failed. No prompt or label was changed to remove them.

## Thinking controls and paired experiment

Live `/api/show`: Gemma `thinking.values=[false,true]`, `default=false`; GPT-OSS values are `low`, `medium`, `high`. Gemma `think:"low"` is unsupported; observed legacy replays produced no thinking. The final router sends explicit `false` to Gemma and preserves valid GPT-OSS levels. See [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking) and [Gemma renderer](https://github.com/ollama/ollama/blob/main/model/renderers/gemma4.go).

Twenty identical paired development inputs per arm, deterministic randomized interleaving (seed 20261102), Gemma only. An explicit 90-second experimental ceiling avoids censoring the thinking-quality comparison; production remains 6 seconds per attempt. No prompts, schemas or labels varied between arms.

- Thinking disabled: n=20, p50 1046.6 ms, p95 1834.6 ms, max 6020.5 ms; F1 1.000, strict hallucination count 0 (n=20).
- Thinking enabled: n=20, p50 1223.9 ms, p95 2099.1 ms, max 2945.3 ms; F1 1.000, strict hallucination count 0 (n=20).

Thinking was present in 20/20 enabled responses and 0/20 disabled responses. No chain-of-thought text was saved.

## Tail timing before and after

- Original HTTP smoke: p50 1267.0 ms, p95 4491 ms, max 19026 ms. p95 nearest-rank excludes the single worst of 20 samples.
- Frozen old extraction-core replay: p50 879.1 ms, p95 1846.6 ms, max 2274.5 ms.
- Final extraction-core replay: p50 1369.5 ms, p95 2149.7 ms, max 8607.5 ms; F1 1.000, strict hallucination count 0 (n=20).

The new replay's p95 is higher than the frozen replay. These sequential samples do not establish a causal latency improvement. Cloud/provider and client timing varied. The timeout behavior is verified directly, not inferred from p95.

Historical slow runs (≥2000 ms) have no stored attempt traces:
- Trial 4: 2522 ms — model/attempt/cause unavailable.
- Trial 9: 4491 ms — model/attempt/cause unavailable.
- Trial 11: 19026 ms — model/attempt/cause unavailable.
- Trial 16: 2092 ms — model/attempt/cause unavailable.

The old artifact saved only stage latencies. Its top-level model is the final trial model. The stateless route did not write these requests into `turns`, so attributing those historical delays to repair, fallback, 429 or generation would be fabrication.

Every newly observed slow run is listed below and in `slow-runs.json`. Separate generation/queue durations were not returned by Cloud; “single initial request” does not prove compute-only generation delay. Server `total_duration` and request wall time are retained.

- frozen_gateway_replay trial 7 legacy gateway-07: 2274.5 ms; single_initial_request; attempt 1 gemma4:31b initial/response 2273.5 ms, server total 1040.8 ms.
- thinking_AB trial 6 true case-09: 2099.1 ms; single_initial_request; attempt 1 gemma4:31b initial/success 2096.2 ms, server total 1731.8 ms.
- thinking_AB trial 18 true case-27: 2945.3 ms; single_initial_request; attempt 1 gemma4:31b initial/success 2942.8 ms, server total 2573.5 ms.
- thinking_AB trial 20 false case-30: 6020.5 ms; single_initial_request; attempt 1 gemma4:31b initial/success 6017.9 ms, server total 5648.6 ms.
- development_before  case-12: 2335.0 ms; single_initial_request; attempt 1 gpt-oss:20b initial/response 2335.3 ms, server total 1052.0 ms.
- quality_after  case-09: 2711.0 ms; single_initial_request; attempt 1 gpt-oss:20b initial/success 2711.0 ms, server total 1457.4 ms.
- quality_after  case-12: 2308.0 ms; single_initial_request; attempt 1 gpt-oss:20b initial/success 2308.8 ms, server total 1133.2 ms.
- quality_after  case-31: 2420.0 ms; single_initial_request; attempt 1 gpt-oss:20b initial/success 2420.4 ms, server total 1207.6 ms.
- quality_after  case-32: 2601.0 ms; single_initial_request; attempt 1 gpt-oss:20b initial/success 2601.8 ms, server total 1423.4 ms.
- quality_after  heldout-01: 2196.0 ms; single_initial_request; attempt 1 gpt-oss:20b initial/success 2196.4 ms, server total 1766.2 ms.
- quality_after  heldout-09: 3092.0 ms; single_initial_request; attempt 1 gemma4:31b initial/success 3092.5 ms, server total 1697.2 ms.
- gateway_after trial 6 policy gateway-06: 8607.5 ms; timeout, model_fallback; attempt 1 gemma4:31b initial/timeout 6001.5 ms; attempt 2 gpt-oss:20b initial/success 2604.4 ms, server total 1288.9 ms.
- gateway_after trial 11 policy gateway-11: 2149.7 ms; single_initial_request; attempt 1 gemma4:31b initial/success 2147.9 ms, server total 701.4 ms.

The final trial 6 demonstrates a 6001.5 ms Gemma timeout followed by a successful 2604.4 ms GPT-OSS attempt, totaling 8607.5 ms. Timeouts skip that model, without a same-model transport retry. JSON repair and HTTP 429 retry remain separately labelled/tested.

## Reproduction

From `khoj-backend`:

```sh
.venv/bin/python scripts/eval_extraction.py --heldout evals/extraction/heldout.v1.jsonl --output ../artifacts/b2-followup/quality-after.json
.venv/bin/python scripts/benchmark_extraction.py --arms false,true --attempt-timeout 90 --output ../artifacts/b2-followup/think-paired-20.json
.venv/bin/python scripts/benchmark_extraction.py --gateway-input --arms policy --output ../artifacts/b2-followup/gateway-after-20.json
.venv/bin/python -m scripts.report_extraction_followup
```

Live evaluation exits nonzero for any strict false positive or provider failure. Fake CI checks the harness with an intentionally ungrounded extra field; it does not establish model quality. `models.yaml` configures `attempt_timeout_seconds: 6`. Future smoke reports and `turns.models.attempts` store per-attempt model, phase, retry, timeout, wall/server timing and outcome, including exhausted analyses.
