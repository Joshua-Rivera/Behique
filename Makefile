.PHONY: lint test eval run docker

lint:
	uv run ruff check . && uv run ruff format --check .

test:
	uv run pytest --cov=behique

eval:
	uv run python eval/run.py

run:
	uv run uvicorn behique.main:app --host 127.0.0.1 --port 8000

docker:
	docker compose up --build
