<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Repository boundaries

- Frontend commands run in `frontend/`; its installed Next.js guides are in
  `frontend/node_modules/next/dist/docs/`. Read `frontend/AGENTS.md` before frontend work.
- Backend commands run in `khoj-backend/`. Keep its lockfiles, migrations and eval corpora there.
- Use `make help` for root command entry points; see `docs/repository-structure.md` for placement.
- Preserve frozen prompts, schemas, eval labels and baseline hashes unless the task requires changing them.
- Never version environments, private captures/recordings, databases or generated run outputs.
