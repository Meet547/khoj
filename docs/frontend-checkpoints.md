# Frontend execution checkpoints

Historical checkpoints below predate the directory cleanup. Frontend source, tests and tool
configuration now live in `frontend/`; artifact paths remain relative to the repository root.
See [current project status](project-status.md) for the latest readiness and validation.

## F0 — accepted

Commit 581bdcd. Responsive layout, mobile dock clearance and scroll behavior, quiet task navigation,
one intake H1, input microphone/editable transcript, 28-second clip timer, ten-language preferences,
self-hosted Indic serif fonts, coverage/FIR copy and bands-only citizen wording.

Acceptance evidence: `artifacts/f0/accepted/`, including the 12 requested en/hi screenshots and two
Tamil typography screenshots. TypeScript, ESLint, 12 unit tests, five browser checks and the build passed.

## F1 — accepted

Application routes and features moved into `src/`, with marketing/app route groups and thin pages.
`src/styles/tokens.css` centralizes the existing design values; existing layouts were preserved.
The zod endpoint schemas are the source of frontend API types. The sole fetch wrapper validates
responses, includes cookies, accepts cancellation/idempotency keys and maps typed errors.
MSW provides session/turn/edit/photos/confirm/search and speech/role-restriction fixtures, including
empty/error/slow/low-confidence/microphone-denied scenarios. STT/turn/search fixture delays are
1.5/2/3 seconds. No transcription is fabricated from a user's microphone recording.

Cookie endpoints pass through MSW to a same-origin mock server: a service worker cannot create
HttpOnly cookies. This bridge is server-only, disabled in live mode and KHOJ_ENV=production,
and stores only phone HMACs plus masked suffixes, not plaintext phone numbers. Its case metadata
is temporary and is not a real police report. B2 remains responsible for authoritative intake/save
validation and durable records. The live proxy uses server-only KHOJ_BACKEND_URL.

Recorder, silence detection, playback, summary card and intake field definitions are separated.
The larger existing Describe/Photo/Check/Save sections stay in Report.tsx, and the marketing sections
stay in Landing.tsx; their behavioral rebuilds belong to F3 and later frontend phases. No files
remain in the old root app/components/lib/messages directories. No empty placeholder components
were added merely to match a directory diagram.

Checks: TypeScript, ESLint, 25 Vitest tests (including schema/error/privacy/transport/preferences/
recording-limit checks), five Playwright layout/language checks, and production build passed.
ESLint bans direct fetch outside lib/api and bans dangerouslySetInnerHTML.

## F2 — implemented and verified

AuthProvider restores the cookie session, handles login/logout and rejects stale auth responses.
OTP uses a fixed +91 prefix, validated/masked mobile input, six keyboard/paste-friendly code boxes,
a 30-second resend countdown, editable errors and the persistent demo-code helper. Mobile code
inputs use two rows to retain 48px targets. Phone input is cleared after verification; tokens never
enter JS storage. Login redirects accept only safe local destinations.

Guests can search and begin intake. Sign-in appears only at Save after confirmed read-back.
The header exposes the last two phone digits, My cases and Logout. Cases and case details require
authentication and ownership; /officer remains a role-guarded placeholder. The server-only demo
bridge simulates send/verify limits, wrong codes, rotating refresh and cookie revocation. Its
temporary intake gate prevents an ordinary direct save without read-back; it is not the B2
authoritative extraction/state machine and is disabled outside mock environments.

Final verification: strict TypeScript, ESLint, 36 unit tests, 10 Playwright tests against the
production build, and `next build --webpack` passed. Browser checks include 360/390/1366px layouts,
language persistence, wrong OTP correction, safe redirects, guest search, report-to-case saving,
HttpOnly/Secure cookies, logout, role/rate/CSRF behavior and cross-account case denial.

`artifacts/frontend-final/` contains 14 final screenshots and geometry checks (en/hi home, report
and search at both requested sizes, plus Tamil home typography). `artifacts/f2/accepted/` contains
OTP/case screenshots and the successful report-flow recording. Automated axe WCAG A/AA scans found
zero violations on mobile home, report input/summary, search and login; this is automated coverage,
not a complete manual WCAG certification.

The final standard Lighthouse mobile homepage run scored **90 performance / 100 accessibility**,
LCP 3.7s, CLS 0 (`artifacts/quality/lighthouse-final.json`). The loading shell reserves a viewport,
the hero tile is 79,776 bytes, offscreen portraits load as they approach, and fonts use local WOFF2
with swap. Locale catalogs and auth code load separately. The original 150KB initial-JS budget is
still open: the measured run transfers about 216KB of scripts including deferred auth (~187KB
before that import). The stricter F5 LCP ≤2.5s and JS budget require further work; they are not
reported as passed. This does not block the independently authorized F0 → F2 functional work.

## Requested backend inputs

`artifacts/zipnet-inspection.zip` contains the inspector's discovery.json, table.html and
Punjab-filtered after_filter.png. Direct POST endpoint: `/Victims/GetMissingPersonsData/`.
The inspector now selects the observed State control instead of the first dropdown (Status).
These are discovery fixtures, not an implemented B3 ingestion pipeline or a permission review.
Raw local fixtures are ignored by Git.

`artifacts/b1/hindi-synthetic-8s.wav` is synthetic Gnani speech, 8 seconds at 16 kHz mono.
It is labelled synthetic and all details are fictional. It does not represent a consenting human
recording. Human/real-world STT quality and full B1 live gateway acceptance remain separate checks.
