# KHOJ backend — B0 foundation + B1 gateway + B2 intake

This directory owns the FastAPI application, its operational tools, migrations and evaluation inputs.
See [current project status](../docs/project-status.md) for the latest readiness; the B0 checkpoint
below is retained as historical evidence.
The implementation follows [the architecture](../docs/architecture.md) and
[the phase prompts](../docs/phase-plan.md). B1 adds stateless speech and grounded extraction
to B0's authentication and dependency health. The ZIPNET crawler and matching code remain
private. B2 adds durable LangGraph intake, authenticated confirmation, and atomic case filing.
See [B2 intake: API, deployment, demo and evals](../docs/intake.md).

## B1 gateway

- `POST /api/voice/stt`: multipart `audio`, `lang` (default `hi`, or `auto`), optional `topic`.
  Accepts browser WebM through FFmpeg conversion to 16 kHz mono WAV. Uploads above 2 MiB
  return 413; clips above 30 seconds return 422 with `retryable=false`.
  Returns `{transcript, detectedLang, empty}`; detected language retains Gnani's code (`hi-IN`).
- `POST /api/voice/tts`: JSON `{text, lang}`; streams `audio/mpeg`. `X-Audio-URL` and
  `Location` contain a signed cached-audio URL; `X-TTS-Cache` is `hit` or `miss`.
  Cache hits skip Gnani. The key is SHA256 of `text|lang|voice|model|speed`.
  `tts_prepare` uses `spell_id`, spelling case IDs and digit strings before synthesis.
- `POST /api/llm/turn`: JSON `{transcript, lang}`; returns `intent`, evidence-grounded
  `fields`, `dropped` count, `model`, `latencyMs`, `degraded`, and `skipped`.
  Contact/ID data is redacted before extraction. This stateless helper is separate from
  B2's conversational `/api/turn`.
- `GET /api/admin/health`: admin session required; re-probes Ollama `/api/tags` and lists
  missing primary/fallback/override models by role. The startup probe is bounded to 10 seconds;
  provider outages log degradation and do not prevent startup. The public `/api/health`
  continues to check PostgreSQL and Redis.
- `GET /api/admin/usage`: admin session required; UTC date, per-role calls/tokens,
  configured limits, threshold flags and disabled status. Each actual provider attempt
  counts, including retries, repairs and failures. Prompt + completion tokens count when
  returned. Budget admission is atomic across instances; token totals become known after
  responses, so already-running requests may exceed a token threshold. At either threshold,
  `compare`/`explain` are skipped with `degraded=true, skipped=true`; essential roles continue
  with degradation. Set `enabled: false` in `config/models.yaml` to disable a role explicitly.

Gnani STT acquires the process semaphore first, then an account-scoped Redis lease, both
within a total 8-second acquisition deadline. Busy requests return 429 with
`{error: {code: "busy", message: "busy", retryable: true}}` and `Retry-After: 1`.
Leases expire after 300 seconds if a worker dies; provider work is bounded to 270 seconds.
All API instances using the same Gnani key must use the same Redis and `GNANI_STT_SLOTS`.
Redis outages fail closed. Providers' error bodies and transcripts are not logged.

Set `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and `R2_BUCKET` for private
R2 storage with SigV4 signed URLs. Development/test without R2 uses `.cache/tts` (override
with `TTS_CACHE_DIR`), atomic private file writes, and HMAC signed URLs. Staging/production
require R2. `TTS_URL_TTL` defaults to 900 seconds. Set `KHOJ_TTS_VOICE`, `TTS_MODEL` and
`TTS_SPEED` to change synthesis settings. The smoke script always uses a fresh temporary
local cache to force a real synthesis request, leaving only the requested output MP3.

```sh
cd khoj-backend
# Uses the existing ignored .env; Redis and FFmpeg must be available.
.venv/bin/python scripts/smoke_live.py
# Optional supplied sample/output locations:
.venv/bin/python scripts/smoke_live.py --sample ../artifacts/b1/hindi-synthetic-8s.wav --output out.mp3
# Real providers + playback decoding (excluded from ordinary pytest):
.venv/bin/pytest -m live tests/test_live.py -s
```

Both `GNANI_API_KEY` and `OLLAMA_API_KEY` are required, from the environment or the backend
`.env`. No microphone recording occurs. The default input is the user-selected, bundled,
labelled synthetic 8-second Hindi WAV. Transcript and extraction print to the console;
they are not saved. See [B1 live verification](../artifacts/b1/README.md) for measured results.

## Start with Docker Compose

Requires Docker Desktop (or a compatible Docker engine with Compose) and uv.

```sh
cd khoj-backend
make install
make env                 # once; refuses to overwrite an existing .env
make up
```

A private, ignored `.env` already exists in the current local workspace. Do not run `make env`
again unless setting up a fresh checkout. It generates random JWT, phone HMAC and AES-GCM keys
with file permissions `0600`; no secret is printed. Keep keys stable across restarts.
Never commit `.env` or copy it into an image.

Compose starts PostgreSQL 16, Redis 7, a one-shot migration container, the API on
`http://localhost:8000`, and an arq worker. The API and worker wait for migrations to succeed.
Ports bind only to loopback. Database volumes persist across `make down`; it does not delete data.
The migration container uses the database owner. API and worker use `khoj_app`, with data access
but no table creation/deletion rights. The checked-in database passwords are **local Compose
credentials only**; production provisioning and secret management belong to B6.

`init_app_role.sql` runs on a fresh Compose database volume. For an existing volume, create/grant
the runtime role through your database administrator before switching to these credentials.

## Demo authentication

```sh
curl --fail http://localhost:8000/api/health
curl --fail -c /tmp/khoj-demo-cookies -H 'Content-Type: application/json' \
  -d '{"phone":"9000000001"}' http://localhost:8000/api/auth/otp/send
curl --fail -b /tmp/khoj-demo-cookies -c /tmp/khoj-demo-cookies \
  -H 'Content-Type: application/json' \
  -d '{"phone":"9000000001","code":"123456"}' \
  http://localhost:8000/api/auth/otp/verify
curl --fail -b /tmp/khoj-demo-cookies http://localhost:8000/api/auth/me
rm /tmp/khoj-demo-cookies
```

OTP `123456` works for valid 10-digit Indian mobile numbers beginning with 6–9 **after a send
request**. Challenges expire after five minutes and are consumed atomically. Five sends and ten
verification attempts per phone per hour are permitted, with additional IP limits. Wrong-code
attempts count. Redis failures fail closed. Forwarded IP headers are not trusted by default;
configure trusted proxy boundaries before deploying behind a proxy.

Demo accounts: `9000000001` citizen, `9000000002` volunteer, `9000000003` officer,
`9000000004` admin. Other valid demo numbers get the citizen role. `make seed` idempotently adds
these accounts, a gazetteer stub and a deliberately uncalibrated scoring placeholder.
It never creates demo accounts when `DEMO_AUTH=0`.

- Phone lookup uses HMAC-SHA256; stored contact values use AES-256-GCM with random nonces.
- Access JWTs last 15 minutes and contain identity/role plus standard validity/session claims,
  never phone numbers. The database remains authoritative for roles and session revocation.
- `khoj_session` and `khoj_refresh` are always HttpOnly, Secure and SameSite=Lax. The refresh
  cookie is scoped to `/api/auth`. Use HTTPS for browser integration; localhost curl is sufficient
  for the command-line smoke check. Tokens are never returned in JSON.
- `POST /api/auth/refresh` rotates the opaque refresh token. Replaying a consumed token revokes
  the whole session family, including existing access JWTs. Logout also revokes server-side state.
- Production refuses `DEMO_AUTH=1`. With demo disabled, the unconfigured real OTP adapter returns
  503; it never silently accepts demo codes or sends messages.
- Mutation requests check browser Origin/Fetch Metadata. Same-origin frontend proxy setup is in F1.

## Development and checks

```sh
make install
make check               # ruff, format, strict mypy app/, pytest
make migrate             # local DATABASE_URL, never implicitly on API startup
make seed
# Optional, from the repository root:
# uv run --project khoj-backend pre-commit install -c khoj-backend/.pre-commit-config.yaml
```

PostgreSQL integration tests are opt-in locally and mandatory in the provided CI workflow.
Use a **disposable database whose name ends in `_test`**; tests perform upgrade → downgrade →
upgrade, then truncate application tables between tests. Only Redis database 15 may be cleared
by the test suite.

```sh
KHOJ_ENV=test \
TEST_DATABASE_URL=postgresql+asyncpg://khoj:khoj@localhost:5432/khoj_test \
TEST_REDIS_URL=redis://localhost:6379/15 \
uv run pytest -ra
```

Without `TEST_DATABASE_URL`, database tests explicitly skip; they do not substitute SQLite.
Without `TEST_REDIS_URL`, Redis logic uses fakeredis with Lua. `live` tests are excluded by default;
B1 includes credentialed provider checks. Dependencies are pinned in `uv.lock` and exported with hashes
to `requirements.lock` for Docker. Regenerate both together after dependency changes.

Models cover the complete section 11 schema plus auth session/refresh-token tables. Migration
0001 uses a frozen SQL snapshot, so future ORM changes cannot mutate migration history. Downgrade
removes application objects and leaves shared PostgreSQL extensions installed. Optional pgvector
is attempted only with `ENABLE_PGVECTOR=1` and only when available; no B0 code depends on vectors.

All person access must use `app/db/repo/persons.py`. Citizens can access public missing-person
records only; volunteers cannot access officer-only records or unidentified bodies. Restricted
reads are audited in a separate transaction, surviving later caller rollbacks; write audits share
the mutation transaction. The owner-scoped citizen intake writer is intentionally left to B2.

Structured application logs include a request ID and safe event names. Validation and unexpected
errors do not echo submitted inputs or exception strings. `GET /api/health` actually checks both
PostgreSQL and Redis and returns 503 if either is unavailable.

## Current verification checkpoint (1 November 2026)

- Ruff and formatting: passed.
- Strict mypy: passed for all 36 application files, including preserved adapters/prototype modules.
- Full pytest run against real isolated PostgreSQL 15 and Redis 7.4.2: **54 passed**.
- Migration upgrade/downgrade/re-apply and ORM/schema parity: passed.
- Real HTTP curl health/login/me/refresh/logout smoke: passed.
- arq worker startup: passed.
- Existing frontend: typecheck and all 12 unit tests passed; frontend source not changed in B0.
- Docker Compose configuration: parsed and tested structurally. **Images and `make up` have not
  been executed because this machine has no Docker runtime.** CI targets PostgreSQL 16; that
  container version has not been tested locally. GitHub Actions has been authored, not executed
  on a hosted runner.

B0 implementation is ready for its remaining Compose acceptance gate. Do not label this phase
fully accepted until `make up` and the login check pass on Docker. Per the user's instruction,
frontend F0 → F1 → F2 proceeded independently of this runtime gate. See
`../docs/frontend-checkpoints.md` for frontend verification. Remaining implementation order:
F3 → B3 → B4 → F4 → B5 → F5 → B6 → F6.

## Inputs for later phases

B1 has passed the real STT → grounded model extraction → TTS smoke using the labelled
synthetic eight-second Hindi clip in `../artifacts/b1/`. A consenting human sample remains
useful for speech-quality evaluation; the synthetic clip verifies API integration.
Provider keys are configured only in the ignored local environment file. B3 discovery fixtures
were collected by the inspector and packaged in `../artifacts/zipnet-inspection.zip`; a crawler
contact address and production connector remain future work. Deployment later needs the chosen
Render/Vercel/R2 accounts, allowed origins and
operational contacts. Ask for each input at its phase, without placing credentials in chat or code.
