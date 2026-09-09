.PHONY: run test seed

VENV=.venv/bin

run:
	$(VENV)/uvicorn app.main:app --reload --port 8000

test:
	$(VENV)/python -m pytest -q

seed:
	$(VENV)/python -m app.seed
