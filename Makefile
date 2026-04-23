.PHONY: up down reseed logs test lint type fmt shell

up:
	docker compose up -d
	@echo "Waiting for API..."
	@until curl -sf http://localhost:8000/api/v1/health > /dev/null; do sleep 1; done
	@echo "Up. API: http://localhost:8000"

down:
	docker compose down

reseed:
	docker compose run --rm db-init python manage.py seed_demo --force

logs:
	docker compose logs -f

test:
	cd apps/api && pytest -v

lint:
	cd apps/api && ruff check . && ruff format --check .

type:
	cd apps/api && mypy hhps tenancy accounts core seed

fmt:
	cd apps/api && ruff format . && ruff check --fix .

shell:
	docker compose exec api-django python manage.py shell
