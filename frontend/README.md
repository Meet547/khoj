# KHOJ frontend

Next.js and React application for multilingual missing/found-person intake and search.
The current user journey uses explicit demonstration data; completing the durable backend
intake integration is the next frontend phase. See the [project status](../docs/project-status.md).

## Develop

From this directory, with Node.js 22.6+:

```sh
npm ci
cp .env.example .env.local  # First checkout only; preserve existing local configuration.
npm run dev
```

Open http://localhost:3000. The template enables mock mode and demo authentication.
Provider secrets belong exclusively in `../khoj-backend/.env`.
See the [root guide](../README.md#configuration) for backend proxy configuration.

## Directory boundaries

- `src/app/`: Next.js routes and thin page entry points.
- `src/features/`: auth, intake, case, search, voice and marketing behavior.
- `src/components/`: shared layout, UI and decorative artwork components.
- `src/lib/`: validated API transport, internationalization, storage and utilities.
- `src/messages/`: ten locale catalogs; UI coverage does not imply backend language approval.
- `src/mocks/`: clearly separated browser/server simulation and fictional input data.
- `src/styles/`: design tokens and application styles.
- `public/`: runtime artwork, icons, fonts and their license notices.
- `tests/unit/`, `tests/e2e/`: unit/component and browser coverage.
- `scripts/`: UI audits and layout captures; output goes to repository-level `../artifacts/`.

React components use PascalCase, hooks use `useName`, ordinary TypeScript modules use descriptive
lowercase/kebab-case names, and Next.js reserved filenames retain framework conventions.
Keep feature behavior with its feature; promote code to shared modules only when it is reused.

## Checks

```sh
npm run typecheck
npm run lint
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

`npm ci` regenerates the ignored MSW worker. Type checking regenerates ignored Next.js declarations.
Run `node scripts/audit-ui.mjs` or `node scripts/capture-layout.mjs` against a running application
to generate local evidence. `E2E_BASE_URL` selects an existing server; `SCREENSHOT_DIR` overrides
the capture destination. Build outputs and local environments stay untracked.
