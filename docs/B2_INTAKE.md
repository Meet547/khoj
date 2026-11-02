# B2: durable conversational intake

B2 implements architecture sections 5–7 using LangGraph 1.2 and the PostgreSQL checkpointer.
Prompts and all ten language template files load at API startup. Prompt SHA256 hashes and
model attempt trails are recorded in `turns.models`; unsupported evidence is recorded in
`turns.ungrounded`. The runtime role performs no checkpoint DDL.

## Install, migrate and prepare speech

From `khoj-backend`:

```sh
uv sync --extra dev --frozen
# Use the migration/owner DATABASE_URL for Alembic, not the restricted runtime role.
uv run alembic upgrade head
uv run python scripts/pregen_tts.py --langs en,hi
# Optional machine-translated languages, for development review only:
uv run python scripts/pregen_tts.py --langs all
```

Migration 0002 adds session ownership, clip/idempotency storage, a transactional matching
outbox, durable dynamic speech segments, and the frozen LangGraph checkpoint schema.
The migration role's default table grants must include the runtime role, as in
`scripts/init_app_role.sql`. Migration downgrade removes B2 data/checkpoints; it is exercised
only on disposable databases in tests.

The API Docker entrypoint runs pre-generation when `KHOJ_PREGEN_TTS=1` before accepting
traffic. `KHOJ_TTS_LANGS` defaults to `en,hi`. Pre-generation skips cached objects. Enable
this deployment step after configuring the private R2 bucket. Static utterances (including
individual sentences of multi-sentence templates and every field-specific clarification)
are cache-only in requests. An absent cached utterance yields captions and a null audio URL;
it never triggers request-time Gnani synthesis. Hindi/English wording is reviewed in the
implementation; the other eight complete machine translations carry `needs_review: true`
and are rejected in production until reviewed.

## API contract

- `POST /api/session` with `{kind: "missing" | "found", lang}` returns `{sessionId}` and
  sets a private, Secure, HttpOnly guest cookie. Authentication is requested only at save.
- `POST /api/turn` takes multipart `sessionId`, exactly one of `text` or `audio`, and optional
  `clipIndex`, `finalClip`, `turnId`. For multiple clips, send consecutive indices starting
  at 0 with a stable `turnId`; set `finalClip=false` until the final clip. Intermediate clips
  return the concatenated transcript without running extraction. Each audio clip uses the
  B1 size/FFmpeg/duration/STT pipeline and is then discarded. Supported detected languages
  switch the conversation language, subject to the production review gate.
- `POST /api/draft/edit` takes `{sessionId, field, value}`. Direct edits are explicit
  corrections; their confidence is high and they are marked confirmed.
- `POST /api/photos` takes multipart `sessionId`, `photo`. It accepts JPEG/PNG/WebP up to
  10 MiB/20 megapixels, re-encodes JPEG without EXIF, and stores the object privately. Vision
  output is restricted to `clothing`, `marks`, `scene`; it is not used to identify anyone.
- `POST /api/confirm` takes `{sessionId, consent: true}` and requires a signed-in user.
  It resumes `interrupt()`, saves once, and returns `{caseNo, stage, matchingQueued}`.
- `GET /api/session/{sessionId}` rehydrates the current response after reconnecting.

Preserve the guest cookie across reconnects. Session access is scoped to that private
cookie before save, and to the authenticated owner after save. Session creation, turns,
edits and photo uploads accept `Idempotency-Key`; keep the same cookie and key when retrying
one request. Confirmation is naturally idempotent through the unique report/session key.
The API rejects reuse of a key with different input. Per-session PostgreSQL advisory locks
serialize mutation across instances.

Turn responses preserve `{transcript, replyText, replyAudioUrl, draft, stage, nextField,
readbackText}` and add `replyAudioUrls`, `conflicts`, `degraded`. `replyAudioUrls` is ordered
by sentence and may contain null entries for unavailable speech. Dynamic sentences synthesize
concurrently within `GNANI_TTS_SLOTS`. A cached opening sentence is returned immediately;
otherwise the response waits only for the first dynamic sentence. Later URLs independently
wait for their segment and can regenerate it from the database
after a process restart. The legacy `replyAudioUrl` is null for missing/failed known segments.
Late audio failures return an audio-specific 503; they never roll back or fail the text turn.
Clients retain captions and skip failed audio segments.

## Graph and persistence

The nodes are `load_draft → analyze_turn → ground → merge → gap_check → ask_next/readback`,
then `record_turn`, and a real LangGraph `confirm` interrupt. `Command(resume=...)` routes
changes back into analysis or approved saves through `require_auth → persist → enqueue_match`.
Checkpoint durability is synchronous at each node; `thread_id` is the session UUID.

Safety triage runs before extraction, returning static localized emergency/cancel/help text.
Emergency templates use 112 and Child Helpline 1098, verified against the
[Ministry of Women and Child Development](https://www.spniwcd.wcd.gov.in/child-helpline).
Prompts wrap escaped user text in `<user_message>` and declare it untrusted. LLM output can
supply descriptions; it cannot invoke confirmation, matching, alerts, or other tools.

Code merges grounded fields, asks about conflicts instead of overwriting, and asks at most
three targeted questions in discriminative order. Asked/skipped fields are not re-asked.
An unresolved conflict blocks confirmation and can be resolved by a correction or direct edit.
Voice-extracted name/age/place fields carry `confidence: confirm`; typed facts carry `high`.
All fields receive confirmation only after the authenticated read-back approval.

One transaction creates the restricted canonical person via `PersonRepository`, original-script
and transliterated name variants, photo associations, report/case number, watch, case event,
consent and matching outbox entry. Rollback leaves none of these partially written. Replayed
persistence returns the same case. `enqueue_match` uses an idempotent arq job; the regular worker
retries unqueued outbox records every 30 seconds. Jobs go to `khoj:matching`; the B3 matching
worker is responsible for consuming that queue. B2 does not perform matching or send alerts.

## Recorded demo, including actual process kills

```sh
# Uses an already migrated database and real Redis. --fake is deterministic CI mode.
uv run python scripts/demo_intake.py --fake --output ../artifacts/b2/hindi-demo-fake.json
# Real Gnani/Ollama keys; prepares all Hindi static speech first.
uv run python scripts/demo_intake.py --output ../artifacts/b2/hindi-demo-live.json
```

The parent starts three independent Python processes, sends SIGKILL after the second turn,
restarts and reaches the read-back interrupt, sends SIGKILL again, then starts a third process,
signs in with the demo OTP, resumes the interrupt and saves. The JSON recording excludes private
cookies. The script uses synthetic fictional details and demo auth; run it against a separate
local demo database. The checked-in recordings used `khoj_b2_demo`, leaving the application
database unchanged. Real case: `KHJ-2026-00001`; fake case: `KHJ-2026-00002`.

## Verification and evaluation

```sh
# Disposable database name must end in _test. Tests reset its tables.
TEST_DATABASE_URL=postgresql+asyncpg://USER@localhost:5432/khoj_b2_test \
TEST_REDIS_URL=redis://localhost:6379/15 uv run pytest -ra
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run python scripts/eval_extraction.py --fake
uv run python scripts/eval_extraction.py --models chain,gemma4:31b,gpt-oss:20b
uv run python scripts/smoke_live.py --runs 20 --report ../artifacts/b2/latency-live-20.json
```

The fake evaluation deliberately adds an unsupported field to every canned extraction.
Its zero kept-field hallucination gate checks the grounding/evaluation harness, not model
quality. The real evaluation separately measures the production prompt and configured model
chain. See [the dataset contract](../khoj-backend/evals/extraction/README.md) and
[recorded evidence](../artifacts/b2/README.md). CI runs the fake evaluation and process-kill demo
and uploads their JSON recordings. Live tests remain opt-in. Docker startup changes are
structurally checked; Docker containers have not been run on this machine.

## Follow-up: harder hold-out and attempt deadlines

The [B2 follow-up report](../artifacts/b2-followup/README.md) supersedes broad accuracy/latency
interpretations of the initial 30-case result. It retains the original artifacts, adds a frozen
37-case development / 35-case held-out split, and reports category/language metrics. The real
held-out strict zero-FP gate remains failed on three label mismatches; no prompts or labels
were changed to hide them.

`config/models.yaml` now defaults each provider attempt to 6 seconds. A timeout skips that
model and moves to the next; the whole chain may take longer than 6 seconds. Gemma's explicit
boolean thinking setting prevents inheritance of GPT-OSS's `low` level. Attempt traces include
model, repair phase, transport retry, timeout, wall time and available server duration. Both
successful and exhausted analyses write these to the existing `turns.models` JSON. Stateless
smoke reports now retain attempt traces too. The historical 20-run file did not retain them,
so its individual slow-run causes cannot be reconstructed.
