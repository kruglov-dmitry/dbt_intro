.DEFAULT_GOAL := help

PYTHON ?= python3
UV ?= uv
OUTPUT_DIR ?= data/events
START_DATE ?=
DAYS ?= 5
ROWS_PER_DAY ?= 5
SEED ?= 42

.PHONY: help install generate lint format check clean

help: ## Show available commands.
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z_-]+:.*##/ {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Create/update the environment with runtime and development dependencies.
	$(UV) sync --all-groups

generate: ## Create Hive-style Parquet partitions; override variables such as DAYS=5.
	$(UV) run python scripts/generate_events.py --output-dir $(OUTPUT_DIR) $(if $(START_DATE),--start-date $(START_DATE)) --days $(DAYS) --rows-per-day $(ROWS_PER_DAY) --seed $(SEED)

format: ## Format Python and TOML files with Ruff.
	$(UV) run ruff format .

lint: ## Verify formatting and linting without changing files.
	$(UV) run ruff format --check .
	$(UV) run ruff check .

clean: ## Remove locally generated event partitions.
	rm -rf $(OUTPUT_DIR)
