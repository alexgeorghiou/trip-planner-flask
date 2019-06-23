.PHONY: install lint format test run demo docker

VENV ?= .venv
PY := $(VENV)/bin/python

install:
	python -m venv $(VENV)
	$(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

test:
	$(PY) -m pytest -q

demo:
	GEOCODER=fake $(VENV)/bin/flask --app trip_planner.wsgi seed-demo

run:
	$(VENV)/bin/flask --app trip_planner.wsgi run --debug

docker:
	docker compose up --build
