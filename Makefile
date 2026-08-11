.PHONY: up down build migrate seed test lint check-expirations

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up --build -d

migrate:
	alembic upgrade head

seed:
	python scripts/seed.py

test:
	pytest --cov=app tests/

lint:
	ruff check app tests
	black --check app tests
	mypy app

check-expirations:
	curl -X POST http://localhost:8000/api/v1/internal/run-expiry-checks -H "X-Internal-Token: internal-secret-token-change-in-production"
