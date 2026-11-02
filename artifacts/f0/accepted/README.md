# F0 acceptance

Validated 1 November 2026. The screenshots in this directory are the accepted set.

- Mobile content scrolls in a viewport that ends above the dock. Geometry checks verify the two do not overlap; safe-area space is included. Desktop uses header controls with no floating dock.
- Dock hides on downward scroll and returns on upward scroll. Keyboard opening hides it.
- Missing-person intake has one H1; textarea and Organize action fit at 1366×768. Input is also visible at 390×844 and 360×800.
- Mic is inside the description input; voice mode includes an editable transcript. A separate timer stops recording at 28 seconds even when animation frames are throttled.
- First visit offers all ten native-script languages on every route. Choice persists in a cookie and localStorage, with storage failures handled.
- English/Hindi messages are present; other locales are explicitly marked as translation fallbacks. Tamil hero text exercises native-script typography.
- Upright Noto Serif fonts are self-hosted with next/font/local, display swap and no preload of inactive language fonts. Indic tracking is zero and Latin display tracking is capped at -0.01em.
- Coverage and independent-platform/FIR copy are present; task navigation is quiet. Critical safety wording remains in translation files. Citizen-facing demo percentages were replaced with bands.

Checks: TypeScript, ESLint, 12 existing unit tests, 5 Playwright checks, production build, and 14 screenshot/geometry checks passed. The screenshot matrix covers /, /report/missing, /search in en/hi at 1366×768 and 390×844, plus the Tamil home hero at both sizes. Browser microphone permission and live STT remain separate device/provider checks; no human voice recording is represented by these screenshots.
