# B2 verification — 2 November 2026

- Full suite: **126 passed**, with live provider tests excluded from ordinary CI.
- Ruff, formatting and strict mypy passed (55 application files).
- Real and fake Hindi conversations used independent processes and **two SIGKILL restarts**:
  once while collecting, once at the durable confirmation interrupt.
- Real case **KHJ-2026-00001**, fake case **KHJ-2026-00002**, saved in isolated local database
  `khoj_b2_demo`. Direct database checks verified restricted person/report ownership, active
  watch, case event and enqueued matching outbox record. Matching itself belongs to B3.
- Real demo pre-generation prepared **65 Hindi static utterances**. Static requests use
  cached audio only. Dynamic sentence concurrency and early first-sentence delivery were
  tested with controlled transports.
- Real 30-case extraction evaluation: **F1 1.0**, **0 kept-field hallucinations** for Hindi,
  English, Hinglish, Marathi on the configured chain. This is a small seed-set result with
  explicit translation aliases, not a general accuracy claim.

Files:

- `hindi-demo-live.json`: real Gnani/Ollama conversation recording, private cookies omitted.
- `hindi-demo-fake.json`: deterministic CI-equivalent conversation with an injected
  hallucinated field that must be dropped.
- `extraction-live.json`: real model-chain report, with prompt/dataset hashes.
- `extraction-fake.json`: deterministic grounding/metric harness report.
- `latency-live-20.json`: 20 real-provider samples and percentiles, milliseconds.
- `out.mp3`: final smoke audio (ignored by git); decode verified with FFmpeg.

The 20-run gateway smoke measured STT p50 **507.5 ms**, p95 **661 ms**; turn extraction
p50 **1267 ms**, p95 **4491 ms**; uncached TTS p50 **2283.5 ms**, p95 **2776 ms**.
P50 is the median; p95 uses nearest rank. These are individual provider stage measurements
through the B1 HTTP gateway, not full-intake turn percentiles. Every TTS run forced a cache miss.

PostgreSQL migrations (upgrade/downgrade/re-apply), schema parity, session privacy, idempotency,
corrections/conflicts, clip concatenation, EXIF stripping, role-limited vision output,
TTS failures, multilingual safety triage, injection isolation, atomic save rollback/retry,
and Postgres interrupt recovery are covered by the suite. R2 uses mocked transport coverage;
these local demos used the local development cache. Production still blocks eight
`needs_review` language translations. No Docker runtime or hosted CI run was performed here.

Reproduction commands and deployment details: [B2 intake guide](../../docs/B2_INTAKE.md).
