.PHONY: setup venv install run test lint typecheck sanity ml-train ml-train-mostlyai help

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

help:
	@echo "Targets:"
	@echo "  make setup      Create .venv and install package with [dev,ml]"
	@echo "  make run        Launch Gradio UI (requires setup)"
	@echo "  make test       Run unit tests"
	@echo "  make lint       Ruff check"
	@echo "  make typecheck  Mypy on telekom_profiler"
	@echo "  make sanity     Integration sanity script"
	@echo "  make ml-train   Generate synthetic data and train K-Means (300 subs)"
	@echo "  make ml-train-mostlyai  Generate MOSTLY AI data and train K-Means"

setup venv install:
	@bash scripts/setup.sh

run:
	@$(BIN)/python app.py

test:
	@OLLAMA_ENABLED=false PROFILER_MODE=rules $(BIN)/python -m unittest discover -s tests -v

lint:
	@$(BIN)/ruff check telekom_profiler tests scripts

typecheck:
	@$(BIN)/mypy telekom_profiler

sanity:
	@OLLAMA_ENABLED=false PROFILER_MODE=rules $(BIN)/python scripts/sanity_check.py

ml-train:
	@$(BIN)/python scripts/generate_synthetic_data.py --subscribers 300 --seed 42
	@$(BIN)/python scripts/subscriber_profiling.py \
		--input data/raw/private_mobile_usage_300_subscribers_12_months.csv \
		--min-silhouette 0.5

ml-train-mostlyai:
	@$(BIN)/python scripts/generate_synthetic_data_mostlyai.py --subscribers 300 --seed 42
	@$(BIN)/python scripts/subscriber_profiling.py \
		--input data/raw/private_mobile_usage_mostlyai_300_subscribers_12_months.csv \
		--min-silhouette 0.5
