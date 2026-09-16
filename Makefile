.PHONY: help install test lint fmt run report clean

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'

install:  ## install the package and dev dependencies
	pip3 install -e ".[dev]"

test:  ## run the full test suite
	python3 -m pytest

test-fast:  ## run everything except tests that need the full corpus
	python3 -m pytest -m "not corpus"

lint:  ## check style and imports
	python3 -m ruff check src tests

fmt:  ## auto-format
	python3 -m ruff format src tests
	python3 -m ruff check --fix src tests

run:  ## run the pipeline over the challenge scope
	python3 -m liasse run

report:  ## regenerate reports/ from the last run
	python3 -m liasse report

clean:  ## drop intermediate artifacts (reports/ is versioned, keep it)
	rm -rf artifacts/* .pytest_cache
	find src tests -name __pycache__ -type d -exec rm -rf {} +
