.PHONY: up down reseed logs test lint type fmt shell sync

sync:
	cd apps/api && uv sync

up:
	docker compose up -d
	@echo "Waiting for API..."
	@until curl -sf http://localhost:8000/api/v1/health > /dev/null; do sleep 1; done
	@echo "Up. API: http://localhost:8000"

down:
	docker compose down

reseed:
	docker compose run --rm db-init uv run python manage.py seed_demo --force

logs:
	docker compose logs -f

test:
	cd apps/api && uv run pytest -v

lint:
	cd apps/api && uv run ruff check . && uv run ruff format --check .

type:
	cd apps/api && uv run mypy hhps tenancy accounts core seed

fmt:
	cd apps/api && uv run ruff format . && uv run ruff check --fix .

shell:
	docker compose exec api-django uv run python manage.py shell
