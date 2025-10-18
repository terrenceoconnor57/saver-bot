.PHONY: install fmt lint typecheck test all

install:
	pip install -e ".[dev]"

fmt:
	ruff format src/ tests/

lint:
	ruff check src/ tests/

typecheck:
	mypy src/ tests/

test:
	pytest tests/

all: fmt lint typecheck test

