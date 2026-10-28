# macOS can hide uv's editable .pth file, which Python then skips.
export PYTHONPATH := src

.PHONY: install lint format test eval run docker

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest --cov=behique --cov-report=term-missing

eval:
	uv run python eval/run.py --check

run:
	uv run uvicorn behique.main:app --host 127.0.0.1 --port 8000

docker:
	docker compose up --build
