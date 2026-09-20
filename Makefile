# India Market AI Research Terminal: Automation Makefile

.PHONY: test test-verbose run-api run-worker bootstrap health-check docker-up docker-down

test:
	python -m pytest -v

run-api:
	uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	python services/worker.py

bootstrap:
	python scripts/bootstrap_universe.py

health-check:
	python scripts/health_check.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
