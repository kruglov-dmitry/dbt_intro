.DEFAULT_GOAL := help

PYTHON ?= python3
UV ?= uv
OUTPUT_DIR ?= data/instruments
START_DATE ?=
DAYS ?= 5
ROWS_PER_DAY ?= 5
SEED ?= 42
DEFECTS ?=

.PHONY: help install generate lint format check clean

help: ## Show available commands.
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z_-]+:.*##/ {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Create/update the environment with runtime and development dependencies.
	$(UV) sync --all-groups

generate: ## Create Hive-style instrument Parquet partitions; set DEFECTS='DATE:KIND ...'.
	$(UV) run python scripts/generate_events.py --output-dir $(OUTPUT_DIR) $(if $(START_DATE),--start-date $(START_DATE)) --days $(DAYS) --rows-per-day $(ROWS_PER_DAY) --seed $(SEED) $(foreach defect,$(DEFECTS),--defect $(defect))

format: ## Format Python and TOML files with Ruff.
	$(UV) run ruff format .

lint: ## Verify formatting and linting without changing files.
	$(UV) run ruff format --check .
	$(UV) run ruff check .

check: lint ## Run all local verification checks.

clean: ## Remove locally generated instrument-revision partitions.
	rm -rf $(OUTPUT_DIR)
