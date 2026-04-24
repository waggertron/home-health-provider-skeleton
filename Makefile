.PHONY: up down reseed logs test lint type fmt shell sync verify \
        test-node lint-node type-node verify-node verify-all \
        cov cov-node cov-all

# The full set of first-party Python packages — keep in sync with
# apps/api/hhps/settings.py::INSTALLED_APPS (minus django built-ins).
API_APPS := hhps tenancy accounts core seed clinicians patients visits routing messaging scheduling

sync:
	cd apps/api && uv sync --extra dev

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
	cd apps/api && uv run ruff check .
	cd apps/api && uv run ruff format --check .

type:
	cd apps/api && uv run mypy $(API_APPS)

fmt:
	cd apps/api && uv run ruff format .
	cd apps/api && uv run ruff check --fix .

# Run every local check CI runs. Fails fast on the first broken step.
verify: lint type test

# rt-node (Phase 4): TypeScript gateway for WebSocket fanout.
test-node:
	cd apps/rt-node && npm test

type-node:
	cd apps/rt-node && npm run typecheck

verify-node: type-node test-node

verify-all: verify verify-node

# Coverage reports. Python target aborts if overall coverage drops below 80%.
cov:
	cd apps/api && uv run pytest --cov=. --cov-report=term-missing --cov-report=html --cov-fail-under=80

cov-node:
	cd apps/rt-node && npm run coverage

cov-all: cov cov-node

shell:
	docker compose exec api-django uv run python manage.py shell
