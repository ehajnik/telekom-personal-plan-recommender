# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version bumps are driven by [Commitizen](https://commitizen-tools.github.io/commitizen/) from [Conventional Commits](https://www.conventionalcommits.org/) on `main`. The canonical version lives in `pyproject.toml`; runtime reads it via `telekom_profiler.__version__`.

---

## [Unreleased]

### Added

- `requirements-ml.txt` and `requirements-dev.txt` for explicit ML and dev dependency installs (includes `openpyxl`)
- Excel training report: `what_this_check_does` and `proof_shown` columns on every audit row; `proof_examples` sheet with step-by-step arithmetic reviewers can repeat

### Changed

- Ollama defaults tuned for CPU-only workstations: `OLLAMA_TIMEOUT=180`, `OLLAMA_NUM_PREDICT=512`; documented model guidance in configuration and runbook
- Synthetic training CSV export now excludes text labels (`seed_archetype`) to keep K-Means inputs numeric-only

### Added

- Training pipeline now exports `artifacts/training_report.xlsx` with sanity checks, cluster counts, confidence distribution, and feature summary
- Sanity script validates latest raw training CSV schema (numeric columns only, no `seed_archetype`, month bounds, and line-count consistency)

---

## [0.2.0] - 2026-05-19

### Added

- ML PoC: synthetic 12-month usage generator, `subscriber_profiling.py` training pipeline
- K-Means segmentation (k=5) with artifacts under `artifacts/` (scaler, model, cluster map)
- `telekom_profiler.ml` feature engineering, inference, and overlay detection
- Subscriber dropdown in UI; distance table and overlay badges in scoring panel
- Consumer catalog `plans_and_options.md` with SKUs for offer prompts
- `PROFILER_MODE` (`auto` / `ml` / `rules`) and optional `[ml]` dependencies
- ML unit tests and CI train-on-synthetic step (silhouette ≥ 0.5)
- Commitizen-based semver releases (`cz bump`, GitHub **Release** workflow)

### Changed

- Consumer catalog aligned with **Telekom Deutschland** official price lists (MagentaMobil XS–XL, Prepaid, Young, PlusKarte, Travel & Surf)
- Profile scoring uses trained clusters when artifacts present; legacy L1 fallback otherwise
- Ollama/rule providers use ML or rules base per `PROFILER_MODE`
- Rule-based offers bias tariff selection by primary archetype from scoring
- Profile prompts require deterministic primary archetype from code scoring
- UI session uses `gr.State` with `ProfileResult` instead of markdown-only handoff
- Centralised business thresholds in `telekom_profiler/config/thresholds.py`
- Typed `CustomerUsage` validation and clamping; `ProfileResult` state serialisation for Gradio
- Fallback providers when Ollama fails (`OLLAMA_FALLBACK_ON_ERROR`)
- Ollama tuning: `OLLAMA_TIMEOUT`, `OLLAMA_NUM_PREDICT`
- UI scoring summary panel and inference mode indicator
- Structured logging via `telekom_profiler/logging_config.py`
- Technical documentation set under `docs/` including ADR and Ollama runbook
- Developer tooling: Ruff, Mypy, GitHub Actions CI
- Documentation rewritten for enterprise readability and integration clarity
- Removed duplicate root `styles/`, `data/`, and `assets/` directories (package paths only)

### Fixed

- Gradio 6 header width and main column layout CSS
- Engine singleton reset at application startup for correct provider selection

---

## [0.1.0] - 2026-05-19

### Added

- Baseline Gradio application with rule-based and Ollama providers, five B2C archetypes, and Telekom branding
