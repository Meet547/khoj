UV ?= uv
.PHONY: env install up down test check migrate seed

env:
	$(UV) run python scripts/init_env.py
install:
	$(UV) sync --extra dev --frozen
up:
	docker compose up --build -d

down:
	docker compose down

test:
	$(UV) run pytest

check:
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy app
	$(UV) run pytest

migrate:
	$(UV) run alembic upgrade head

seed:
	$(UV) run python -m scripts.seed

.PHONY: pregen-tts demo-intake eval-extraction
pregen-tts:
	$(UV) run python scripts/pregen_tts.py --langs en,hi
demo-intake:
	$(UV) run python scripts/demo_intake.py --fake
eval-extraction:
	$(UV) run python scripts/eval_extraction.py --fake
