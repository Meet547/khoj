# Project status

Reviewed 3 November 2026. KHOJ is an engineering prototype with a real-provider backend intake
pipeline and a verified demo frontend. It has not completed the gates for public production use.
There is no useful single completion percentage: missing integration, safety and operations work
has a different cost from building the existing screens.

## What we have achieved

### Foundation: B0

FastAPI, PostgreSQL migrations, Redis, a worker, dependency health and role-aware access are in
place. Authentication uses secure cookies, server-side revocation and refresh rotation. Phone
lookup/storage uses keyed hashing and encryption. Demo OTP is explicitly separated from production;
real SMS delivery is still unconfigured. Database tests exercise migration reversibility and access
boundaries. Docker definitions exist, but running the Compose stack remains an acceptance gate.

### Voice and models: B1

The real Gnani STT/TTS and Ollama APIs have been exercised. The speech gateway accepts browser
audio, enforces size/duration limits and normalizes audio for transcription. TTS caches private
objects and returns signed URLs. Cross-instance STT leases, model availability probes, role budgets,
retry handling and attempt diagnostics are implemented.

An 8-second **synthetic** Hindi sample produced a transcript, supported extraction and a decodable
MP3. The standalone live run measured STT **508 ms**, extraction **1,330 ms** and uncached TTS
**2,251 ms**. These are individual requests. A later 20-run gateway sample measured STT p50/p95
**507.5/661 ms**, extraction **1,267/4,491 ms** and uncached TTS **2,283.5/2,776 ms**.
These are provider-stage measurements, not full user-turn latency.

### Durable conversational intake: B2

The backend now collects a grounded draft through a LangGraph workflow. Fields retain evidence;
unsupported extracted fields are dropped. Explicit corrections replace values; conflicting claims
trigger clarification. Code chooses follow-up questions and assembles localized read-backs.
Emergency triage runs before the model. Model output cannot directly save cases or send alerts.

PostgreSQL checkpoints preserve conversation state and confirmation interrupts. Both real and
fake Hindi demos survived two process kills and created synthetic cases after authenticated
confirmation. Persistence writes related person, report, name, watch and event records atomically,
then schedules matching work. **Scheduling a match is not an implemented matching engine.**

Photos are sanitized and vision is restricted to visible clothing, marks and scene descriptions.
Static template speech can be pre-generated and is cache-only during requests. Dynamic text is
split and synthesized concurrently into ordered audio URLs. Speech failure preserves the text reply.
Hindi and English templates are available; eight additional backend locales remain blocked in
production pending review.

### Evaluation and tail latency follow-up

The evaluation suite now has **37 development cases** and **35 held-out cases**, covering clean
language, Hinglish, rambling, corrections, conflicts, STT-like errors and injection attempts.
Reporting separates categories, languages and model chains. Frozen prompts, schemas and baseline
sources preserve the experiment boundary.

The development score was **F1 1.000 with zero strict-label mismatches**. Held-out F1 was
**0.927 with three strict-label mismatches**, unchanged before/after router changes. Two mismatches
were equivalent wording and one omitted a spatial qualifier. The strict zero-false-positive live
gate remains failed; the deterministic fake CI evaluation checks the harness, not real model quality.

Gemma's supported thinking configuration was verified as boolean. Twenty paired trials per arm
measured p50/p95 **1,047/1,835 ms** with thinking disabled and **1,224/2,099 ms** enabled;
both scored F1 1.0 on those development inputs. The configured per-attempt deadline is **6 seconds**,
with timeouts recorded before fallback. It does not cap the entire model chain at 6 seconds.

The final same-input replay measured **1,370/2,150 ms**, compared with the frozen older replay's
**879/1,847 ms**. This does not show a speed improvement. One timeout plus fallback took **8.6 s**.
Missing historical attempt traces cannot be reconstructed. See the
[full follow-up findings](../artifacts/b2-followup/README.md).

### Frontend: F0 through F2

The responsive multilingual UI, typed API layer, recording/playback components, demo authentication,
owner-scoped demo case pages and language preferences are implemented. Historical production-browser
verification covered ten scenarios; unit coverage contains 36 tests. Automated mobile accessibility
scans reported zero violations on the tested screens, which is not a manual accessibility audit.

The frontend still uses a demo intake journey. Full F3 integration with the durable backend is the
next major product step. Mock cases and mock search results are not authoritative reports or matches.
The historical Lighthouse mobile score was 90 performance/100 accessibility, with LCP 3.7 seconds.
The stricter LCP and JavaScript budgets remain open.

### Repository and delivery hygiene

The code is published on GitHub `main`. Applications now own their dependencies, configuration,
scripts and tests in separate directories. Shared guides have a documentation index, consistent
filenames and a repository map. Root Make targets delegate to each application. Backend CI includes
PostgreSQL/Redis tests, a deterministic restart demo and evaluation artifacts; frontend CI now
defines type, lint, unit and build checks. A workflow definition is not proof of a hosted passing run.

Secrets, databases, real photos, recordings, private portal captures and generated evidence are
excluded. Published media has synthetic/provenance documentation. R2 paths have mocked coverage;
the recorded live exercises used local development storage.

## What remains, in delivery order

1. **F3: connect the product journey.** Replace the demo intake path with backend sessions, turns,
   ordered audio playback, draft editing, photos, read-back and authenticated confirmation. Verify
   recovery, retry behavior and ownership end to end through the browser.
2. **B3: implement production ingestion and matching.** Validate connector permission/data handling,
   normalize incoming records, consume queued matching work and calibrate evidence-based scoring.
3. **Review, disclosure and notifications.** Complete authorized reviewer workflows, release policy,
   real contact delivery, consent, case lifecycle and audit behavior before alerts reach people.
4. **Close quality and language gates.** Improve held-out extraction without tuning against held-out
   labels, test real-world speech, review remaining translations and meet frontend performance budgets.
5. **Validate operations.** Run containers and hosted CI, configure real OTP and R2, deploy staging,
   prove backup/restore, secret rotation, monitoring, retention/deletion, abuse controls and incident
   procedures. Select a project license before claiming broad reuse rights.

The next useful milestone is a complete browser-to-backend Hindi/English intake that resumes after
restart and saves a private case. A full public matching service requires the later gates above.

## Verification provenance

Before this directory reorganization, local checks passed **135 backend tests**, **36 frontend
tests**, Ruff, strict mypy, TypeScript, ESLint and the frontend production build. Ten browser tests
are an earlier F2 checkpoint. See the [root guide](../README.md#validation-and-measured-limits)
and application READMEs for reproduction commands. The reorganization passed frontend type generation/TypeScript, ESLint, **36 tests** and a production
build. Backend Ruff/formatting, strict mypy (55 application files) and **80 tests** passed;
**55 database-dependent tests skipped** because disposable service URLs were not configured for
this run, and one live test was deselected. The earlier 135-test database run remains historical
evidence. No new real-provider latency/accuracy experiment or hosted CI run was performed.
