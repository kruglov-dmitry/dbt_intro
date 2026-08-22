.DEFAULT_GOAL := help

PYTHON ?= python3
UV ?= uv
OUTPUT_DIR ?= data/events
START_DATE ?= 2026-08-18
DAYS ?= 3
ROWS_PER_DAY ?= 100
SEED ?= 42

.PHONY: help install generate lint format check clean

help: ## Show available commands.
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z_-]+:.*##/ {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Create/update the environment with runtime and development dependencies.
	$(UV) sync --all-groups

generate: ## Create Hive-style Parquet partitions; override variables such as DAYS=5.
	$(UV) run python scripts/generate_events.py --output-dir $(OUTPUT_DIR) --start-date $(START_DATE) --days $(DAYS) --rows-per-day $(ROWS_PER_DAY) --seed $(SEED)

lint: ## Run Ruff lint checks.
	$(UV) run ruff check .

format: ## Format Python and TOML files with Ruff.
	$(UV) run ruff format .

check: ## Verify formatting and linting without changing files.
	$(UV) run ruff format --check .
	$(UV) run ruff check .

clean: ## Remove locally generated event partitions.
	$(PYTHON) -c 'from pathlib import Path; import shutil; shutil.rmtree(Path("$(OUTPUT_DIR)"), ignore_errors=True)'
