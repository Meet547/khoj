# KHOJ · खोज

**Voice-first intake for missing-person support, with evidence-grounded extraction and human review.**

KHOJ helps a person describe someone who is missing or has been found, review what the system
heard, and save a private case. The project combines a multilingual Next.js frontend with a
FastAPI backend, Gnani speech APIs, Ollama model routing, and a durable LangGraph intake pipeline.

> **Project status:** engineering prototype with verified backend intake. The frontend currently
> supports a clearly labelled demonstration workflow. Full frontend-to-intake integration,
> production ingestion, matching, review and notification delivery remain subsequent phases.
> KHOJ is an independent project, not a police or emergency-dispatch service.

[Project status](docs/project-status.md) · [Repository guide](docs/repository-structure.md) ·
[Architecture](docs/architecture.md) · [Backend guide](khoj-backend/README.md) ·
[Intake API and deployment](docs/intake.md) · [Evaluation findings](artifacts/b2-followup/README.md) ·
[Frontend phase notes](docs/frontend-checkpoints.md)

## What works today

- **Multilingual demo UI:** responsive intake, transcript editing, microphone recording, language
  selection, cookie-based demo authentication and owner-scoped demo case pages.
- **Real speech gateway:** browser audio is converted to 16 kHz mono WAV before STT; audio above
  2 MiB or 30 seconds is rejected. TTS uses a private cache and signed audio URLs.
- **Evidence-grounded extraction:** one role-based model call analyzes a turn. Code checks evidence,
  merges corrections, surfaces conflicts and chooses up to three targeted follow-up questions.
- **Durable intake:** PostgreSQL checkpoints survive process restarts and confirmation interrupts.
  Authenticated confirmation saves the case and related records in one transaction.
- **Operational controls:** account-wide STT leases, per-role model budgets, capability probes,
  per-attempt deadlines and structured attempt diagnostics.
- **Private photos:** uploads are re-encoded without EXIF. Vision output is limited to clothing,
  visible marks and scene descriptions; it does not identify people.

Matching jobs are enqueued for the later matching worker. A queued job is not a completed match
or a notification. Public-portal discovery code is experimental and is not a production connector.

## Architecture at a glance

```text
Next.js / React
  └─ same-origin /api proxy
      └─ FastAPI
          ├─ Gnani STT / TTS ── private R2 cache (local disk in development)
          ├─ Ollama role router ── schema validation, retries, deadlines, budgets
          ├─ LangGraph intake ── grounding, merge, questions, read-back, confirmation
          ├─ PostgreSQL ── cases, ownership, audit and durable graph checkpoints
          └─ Redis / arq ── shared admission controls and matching outbox dispatch
```

The browser never receives provider credentials. Matching policy, confirmation and persistence
are application code; a model cannot approve a match, save a case or send an alert by issuing text.

## Repository layout

```text
frontend/                     Next.js app, public assets, npm configuration and frontend tests
  src/app/                    Routes and thin page entry points
  src/features/               Auth, intake, case, search, voice and marketing behavior
  src/lib/                    Typed transport, storage, localization and shared utilities
  scripts/                    UI audits and layout captures
khoj-backend/                  FastAPI app, Python configuration and backend tests
  app/api/                    Authentication, speech, intake and administration endpoints
  app/graph/                  State, nodes, versioned prompts and language templates
  app/db/                     Models, repositories and Alembic migrations
  app/integrations/            Speech, model and private-object adapters
  scripts/                    Setup, demos, speech pre-generation and evaluation tools
  evals/extraction/            Versioned development and held-out JSONL corpora
docs/                         Engineering guides, phase history and current project status
artifacts/                    Provenance, verification notes and frozen regression baselines
Makefile                      Root commands that delegate into each application
```

Run `make help` at the root for application commands. Each application owns its dependencies and
configuration; there is no root npm package. See [the documentation index](docs/README.md).

Generated reports, screenshots, build outputs, private recordings, databases and connector captures
are intentionally excluded. Historical verification notes may refer to local evidence that is not
published. Scripts regenerate the reports; CI uploads its own demo and evaluation artifacts.

## Requirements

- Node.js **22.6 or newer** and npm; the frontend lockfile pins the installed dependency graph.
- Python **3.11 or newer** and [uv](https://docs.astral.sh/uv/); development is verified on Python 3.12.
- PostgreSQL **15+**, Redis **7+** and FFmpeg for the backend.
- Docker with Compose for the container-based local stack, or independently running services.
- Gnani and Ollama API keys for real-provider exercises. Frontend mocks and ordinary backend tests
  do not need provider keys.

## Quick start: frontend demo

From the repository root:

```sh
cd frontend
npm ci
# Fresh checkout only; preserve an existing local environment file.
cp .env.example .env.local
npm run dev
```

Open **http://localhost:3000**. `npm ci` generates the MSW runtime worker from the pinned dependency.
The default template enables `NEXT_PUBLIC_USE_MOCK=1` and `NEXT_PUBLIC_DEMO=1`.

Demo OTP: **123456**. Demo accounts use `9000000001` for citizen, `9000000002` for volunteer,
`9000000003` for officer and `9000000004` for admin. Demo authentication requires a send request
before verification. It does not deliver a real SMS. Mock browser/server data is not a real case
filing, live portal search or production review dashboard.

## Quick start: backend

### Docker Compose

```sh
cd khoj-backend
uv sync --extra dev --frozen
make env                 # Fresh checkout only; refuses to overwrite an existing .env.
# Configure provider credentials in the ignored .env when real speech/models are needed.
docker compose up --build -d
curl --fail http://localhost:8000/api/health
```

Compose starts PostgreSQL, Redis, an owner-credential migration step, a restricted API role and
an arq worker. Published service ports bind to loopback. Database and Redis volumes persist across
`docker compose down`.

The included database passwords are **local development defaults**. Use managed secrets and
separate migration/runtime credentials for deployment. Docker configuration is supplied, but this
workspace's verification used native PostgreSQL and Redis; the containers were not run locally.

### Native services

```sh
cd khoj-backend
uv sync --extra dev --frozen
make env                 # Once on a fresh checkout.
# Set DATABASE_URL and REDIS_URL in .env to your local services.
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

In a second backend terminal, start the worker with `uv run arq app.jobs.worker.WorkerSettings`.
Run migrations with the database owner; the application role should not have DDL privileges.

## Configuration

Frontend `frontend/.env.local` contains public feature flags and a server-only backend origin:

```dotenv
NEXT_PUBLIC_USE_MOCK=0
NEXT_PUBLIC_DEMO=0
NEXT_PUBLIC_API_BASE=
KHOJ_BACKEND_URL=http://127.0.0.1:8000
```

This enables the same-origin API rewrite. It is not a claim that every current frontend flow
already implements the durable backend intake contract; see the F3 integration work in the phase
notes. Use the backend scripts below to exercise that pipeline directly.

Backend configuration lives in the ignored `khoj-backend/.env`. Start from the generated environment
and consult [the template](khoj-backend/.env.example). Important settings include:

- `DATABASE_URL`, `REDIS_URL`: persistence, checkpoints, queues and shared controls.
- `JWT_SECRET`, `PHONE_HMAC_SECRET`, `PHONE_ENC_KEY`: stable, private signing/encryption material.
- `GNANI_API_KEY`, `OLLAMA_API_KEY`: server-side provider access.
- `GNANI_STT_SLOTS`, `GNANI_TTS_SLOTS`: speech concurrency limits.
- `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`: private object storage.
- `KHOJ_PREGEN_TTS=1`, `KHOJ_TTS_LANGS=en,hi`: pre-generate static speech at container startup.
- `KHOJ_ENV`, `DEMO_AUTH`, `ALLOWED_ORIGINS`: environment, authentication mode and origin policy.

Roles, model chains, per-model thinking settings and usage budgets are in
[`khoj-backend/config/models.yaml`](khoj-backend/config/models.yaml). Each provider attempt defaults
to a **6-second deadline**; a timeout advances to the next model. The whole chain can take longer.

Never put credentials in a `NEXT_PUBLIC_` variable, commit an actual `.env`, or use a token in a Git URL.

## Intake API

- `POST /api/session`: start a private missing/found intake session.
- `POST /api/turn`: multipart text or audio; supports ordered multi-clip transcription.
- `POST /api/draft/edit`: make an explicit field correction.
- `POST /api/photos`: attach a private, sanitized photo.
- `POST /api/confirm`: authenticated, consented read-back approval and atomic case creation.
- `GET /api/session/{sessionId}`: reconnect to the durable session.
- `POST /api/voice/stt` and `POST /api/voice/tts`: stateless speech helpers.
- `GET /api/admin/health` and `GET /api/admin/usage`: administrator-only model diagnostics.

Guest sessions use a private cookie. After save, access is owner-scoped. Mutations support
idempotent retries. Turn responses provide captions, draft evidence, stage and ordered audio URLs.
Static speech is cache-only at request time; dynamic sentences synthesize concurrently. TTS failure
does not discard a successful text turn. See [the complete contract](docs/intake.md).

## Reproducible demos and evaluation

With migrated PostgreSQL and Redis available, from `khoj-backend`:

```sh
# Deterministic Hindi conversation; kills/restarts two processes and then saves a synthetic case.
uv run python scripts/demo_intake.py --fake

# Real providers; prepares Hindi static speech first. Use a separate local demo database.
uv run python scripts/demo_intake.py

# Harness regression with an intentionally ungrounded field; not a model-quality measurement.
uv run python scripts/eval_extraction.py --fake --heldout evals/extraction/heldout.v1.jsonl

# Real, frozen-label development + held-out evaluation.
uv run python scripts/eval_extraction.py --heldout evals/extraction/heldout.v1.jsonl

# Paired thinking experiment and real speech latency samples.
uv run python scripts/benchmark_extraction.py --arms false,true --attempt-timeout 90 \
  --output ../artifacts/b2-followup/think-paired-20.json
uv run python scripts/smoke_live.py --runs 20 --report ../artifacts/b2/latency-live-20.json
```

The 90-second override is an experimental measurement ceiling, not the production deadline.
Live exercises consume provider quota and write synthetic cases when the demo script saves them.
The bundled [eight-second Hindi WAV](artifacts/b1/README.md) is explicitly synthetic and contains
fictional details. Private voice material and human recordings are excluded from Git.

## Validation and measured limits

The latest local backend regression completed **135 passing tests**, with the live provider test
excluded from ordinary CI. Ruff, formatting and strict mypy passed. Earlier frontend verification
recorded **36 unit tests** and **10 production-browser tests**; rerun the commands below for your
checkout. GitHub Actions definitions are included; a hosted run is not implied by local results.

The [follow-up evaluation](artifacts/b2-followup/README.md) preserves the uncomfortable results:

- Development: **37 cases, F1 1.000**, zero strict-label mismatches.
- Held-out: **35 cases, F1 0.927**, three strict-label mismatches, unchanged by the router changes.
  Two are equivalent wording; one omits a spatial qualifier. The strict zero-FP live gate remains failed.
- Twenty paired Gemma trials: thinking disabled **1,047 / 1,835 ms** p50/p95; enabled
  **1,224 / 2,099 ms**. Both scored F1 1.0 on those development inputs.
- The final same-input replay was **1,370 / 2,150 ms**, versus the frozen old replay's
  **879 / 1,847 ms**. These samples do not demonstrate a latency improvement.
- A real timeout took approximately 6 seconds before a successful fallback completed the request
  in 8.6 seconds. Historical missing attempt traces cannot be reconstructed.

These small evaluations do not establish general real-world accuracy or production readiness.

```sh
# Frontend
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
# Browser installation is required before browser tests.
npx playwright install chromium
npm run test:e2e

# Backend, from the repository root in a separate terminal
cd khoj-backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -ra
```

For full database tests, set `TEST_DATABASE_URL` to a disposable database whose name ends in
`_test`, and `TEST_REDIS_URL` to Redis database **15**. The suite migrates and clears test data.
Without a database URL, database-dependent tests skip. Live tests are opt-in with `pytest -m live`.

## Security and deployment boundaries

- Real OTP delivery is not configured. Production rejects demo authentication; configure a real
  provider before public use.
- Hindi and English templates are implemented. Eight other backend locales carry `needs_review`
  and are blocked in production pending language review.
- R2 is required for staging/production. Its transport/signing paths have mocked tests; the
  recorded local exercises used development storage, not a live R2 bucket.
- Found-person location/photo disclosure, match release and notifications require the later policy
  and review workflows. No automatic identification or alert delivery is claimed here.
- Portal ingestion, matching consumption of `khoj:matching`, abuse controls, deployment validation,
  incident procedures and retention operations need the remaining implementation/review gates.
- Source control excludes credentials, databases, connector captures, voice libraries, private
  uploads and generated run outputs. Only synthetic runtime assets with recorded provenance,
  curated evaluation inputs and test baselines are published.

Before a public rollout, complete the remaining product integration and operational gates in
[the architecture](docs/architecture.md) and [phase plan](docs/phase-plan.md).

## Contributing

Keep changes scoped and cover behavior with meaningful tests. Do not alter frozen held-out labels
or prompts merely to make an evaluation pass. Read the installed Next.js guides referenced by
`AGENTS.md` before frontend changes. Use private environment files for credentials and generate
verification artifacts locally or in CI. Preserve the distinction between demo behavior and live
backend behavior in code, documentation and review descriptions.

## License

A project-wide license has not been selected. Third-party font/license notices remain with their
assets. Add an explicit license before representing this repository as freely reusable software.
