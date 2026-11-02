# Repository structure and conventions

The repository contains two independently installed applications. The root owns shared guidance,
automation and evidence. Keeping the established `khoj-backend/` name preserves database tooling,
deployment contexts and frozen evaluation references.

```text
KHOJ/
├── .github/workflows/    Hosted checks for each application
├── frontend/            Next.js application, npm lockfile, public assets and frontend tests
├── khoj-backend/         FastAPI application, Python lockfiles, migrations, model config and evals
├── docs/                System design, implementation guides, status and phase history
├── artifacts/           Synthetic test input, source provenance and verification notes
├── AGENTS.md            Repository working instructions
├── Makefile             Commands that delegate into the owning application
└── README.md            Entry point, setup, capabilities and limits
```

## Ownership and placement

Application-specific configuration stays next to that application's dependency manifest.
Install JavaScript dependencies in `frontend/` and Python dependencies in `khoj-backend/`.
There is no root npm package or npm workspace. Use `make help` at the root or run application
commands in their own directories.

Frontend source retains its existing feature boundaries. Backend endpoints live in `app/api/`,
the intake graph in `app/graph/`, persistence in `app/db/`, provider adapters in `app/integrations/`,
and jobs in `app/jobs/`. Existing internal module names are preserved to keep this organization
change separate from architectural refactoring. Versioned prompts, schemas, migration history and
frozen baseline contents are unchanged.

## Naming

- Documentation uses descriptive kebab-case filenames; `README.md` and `AGENTS.md` remain conventional entry points.
- Python modules and tools use `snake_case`; React components use PascalCase and hooks use `useName`.
- Keep framework-reserved route/config names, migration sequence numbers and versioned corpus names.
- Give scripts action-oriented names. Put application scripts beside their application.
- Do not rename published case identifiers, endpoint routes or schema fields for cosmetic consistency.

## Generated and private material

Keep build outputs and caches in the owning application's standard directories. Keep run reports,
screenshots and demos in repository-level `artifacts/`; those generated files are ignored.
Do not move historical evidence merely to make directory names uniform.

Actual environments stay in `frontend/.env.local` and `khoj-backend/.env`; only `.env.example`
templates are versioned. Credentials, databases, private fixtures, recordings and original artwork
remain ignored. The labelled synthetic B1 WAV and frozen regression inputs are intentional source
exceptions. See [the evidence index](../artifacts/README.md).

## Migration from the previous layout

Frontend `src/`, `public/`, `tests/`, `scripts/`, npm files and framework/tool configuration moved
under `frontend/`. Existing local frontend dependencies, environment files and build caches moved
with them; no private data was deleted. Development/build tools should use `frontend/` as their
working directory, including any future frontend hosting project settings.

The guides were renamed to `architecture.md`, `intake.md`, `phase-plan.md` and
`frontend-checkpoints.md`; repository links now use those names. Historical external links to old
GitHub paths can be viewed at the previous commit.
