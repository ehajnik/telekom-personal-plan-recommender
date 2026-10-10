# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version bumps are driven by [Commitizen](https://commitizen-tools.github.io/commitizen/) from [Conventional Commits](https://www.conventionalcommits.org/) on `main`. The canonical version lives in `pyproject.toml`; runtime reads it via `telekom_profiler.__version__`.

---

## Unreleased

### Fix

- **offers**: size tariffs by allowance — cheapest tariff covering usage × (1 + growth) × 1.1. Broad usage customers (~59 GB) were offered MagentaMobil S (30 GB); Prepaid S (1 GB) was offered for up to 3 GB; streaming users at 50 GB were pushed to XL although L (100 GB) fits
- **offers**: remove "MagentaMobil Special" as a €10 add-on (it is a standalone €19.95 tariff), data-volume-triggered PlusKarte, and the unverified Travel Mobil Basic
- **profile**: upsells no longer cite non-existent products ("Data Boost", "EU Roaming Plus", "World Roaming Pack", "MagentaMobil M+"); ML profile shows the customer's own usage next to the profile reference instead of only the cluster centroid
- **catalog**: update to Telekom 2026 facts — prepaid M/L/XL now 20/40/80 GB (since 25.02.2026), prepaid M voice flat to all German networks, postpaid annual non-EU data volume 2–50 GB (since 04.02.2026), PlusKarte+ €14.95, current Travel & Surf passes
- **ml**: committed dataset, centroids and artifacts were produced by an older 7-archetype generator (incl. a "Value optimization candidate" label in the cluster map); regenerated consistently
- **ml**: cluster on slider-observable log usage levels — the 12-feature space classified only 76.8 % of slider-entered subscribers correctly (now 100 %)
- **ml**: trends use one unit everywhere (% per year); previously GB/month slope × 50 in ML and an undefined scale in rules mode
- **llm**: repair retries were capped at 4096 tokens, below the 6144 first-attempt budget; now 1.5× the budget
- **llm**: do not send `temperature` to Anthropic models (current Claude models reject it); replace retired `claude-3-5-sonnet-latest` with `claude-opus-5-5`
- **ui**: block offer generation when sliders changed after profiling; fix "Run profile" placeholder copy
- **deps**: add missing `pyyaml` to `requirements.txt`
- **docs**: correct `OLLAMA_NUM_PREDICT` default (6144), provider source tags, `ollama` → `litellm` dependency, default model consistency (`qwen2.5:7b`)

### Feat

- **ml**: synthetic generator with per-subscriber baselines, relative trends, roaming seasonality and ground-truth sidecar labels
- **ml**: `scripts/evaluate_model.py` — batch and slider-path accuracy, template round-trip, anchor drift, k-selection; wired into CI and `make ml-train`
- **catalog**: structured `domain/catalog.py` with tests that keep it identical to the LLM reference markdown
- **offers**: `recommend()` returns a structured `OfferRecommendation`; offer reports show the sizing calculation and a prepaid/postpaid alternative
- **prompts**: offer prompt receives usage figures and the deterministic sizing as grounding
- **config**: `PROFILER_CONFIG` override and clear error when `app_config.yaml` is missing

## v0.4.0 (2026-05-28)

### Feat

- **ml**: freeze hardcoded profiles from 1000-subscriber baseline
- **ml**: switch to fixed 5-profile frozen-centroid scoring
- **config**: centralize runtime knobs in root YAML
- **ml**: add MOSTLY AI synthetic panel generator
- **ui**: set Telekom logo as Gradio favicon
- **domain**: wrap headline archetype and tariff facts in <mark>
- **prompts**: ask LLM to wrap key facts in <mark> for magenta highlight
- **ui**: render inline HTML in result Markdown for highlight tags
- **ui**: style result Markdown with Telekom magenta highlights
- **ml**: name the family / multi-line profile instead of Profile 6
- **ml**: elbow + silhouette k-selection and Hungarian label matching

### Fix

- **vscode**: use supported Python formatter id
- **config**: raise Ollama completion limit to 2048 tokens
- **providers**: use ML profile provider when Ollama fails in ml mode
- **scoring**: log ML fallback and expose backend metadata on ScoringResult
- **offers**: correct high-data addon and family profile tariff rules
- **engine**: re-score offers from current usage and validate inputs
- **scripts**: correct documented synthetic-data CSV filename pattern

### Refactor

- **ml**: remove Excel training report output

## v0.3.0 (2026-05-21)

### Feat

- **ml**: line-level check_results with PASSED/WARNING/INVALID in Excel
- **ml**: show what each Excel check does with visible proof
- **ml**: add statistician validation sheets to training Excel report
- **ml**: enrich Excel sanity sheet with audit columns and styling
- **ml**: add backward math sanity checks to training Excel report
- **ml**: add numeric-data sanity checks and Excel training report

### Fix

- **ml**: resolve mypy errors in training_report
- **ml**: satisfy ruff lint in training_report
- **ml**: color full Excel audit rows by verdict (green/yellow/red)
- **deps**: add requirements-ml.txt and clearer openpyxl install path
- **ui**: expand layout to nearly full viewport width
- **ui**: revert outer template padding; inset text from panel border
- **ui**: add template dropdown inner padding; English generated text
- **ui**: drop inner wrap border on profile template dropdown only
- **ui**: remove inner border on profile template dropdown text
- **ui**: tighten slider spacing and style profile template dropdown
- **ui**: bordered slider rows with spacing between features
- **ui**: unify Telekom color palette and slider track styling
- **ui**: align layout on shared grid shell with card styling
- **ui**: stack info row, template, then sliders and actions
- **ui**: compact Gradio layout and clarify placeholder copy
- sort imports in package __init__

### Refactor

- **ui**: remove subscriber picker and simplify toolbar

## v0.2.0 (2026-05-20)

### Feat

- **catalog**: align offers with Telekom Deutschland price lists
- **ml**: align profile_characteristics with enterprise centroid schema.
- **ui**: add subscriber picker, distance table, and slider override.
- **ml**: integrate inference, scoring, providers, and catalog prompts.
- **ml**: add synthetic data generator and K-Means training pipeline.
- add logging, operational docs, and configuration reference
- **ui**: add typed state, scoring panel, and layout fixes
- **ollama**: add fallback providers and aligned prompts
- add centralized thresholds and domain validation
- **domain**: add typed models and shared archetype scoring

### Fix

- fix Ruff import ordering in domain modules
- **docs**: correct paths to telekom_profiler package data

### Refactor

- **services**: add ProfilerEngine and pluggable providers

## v0.1.0 (2026-05-19)

### Feat

- add archetype-aligned profile presets for five clusters
- **ui**: add Deutsche Telekom theme and brand styling
- add Gradio private customer profiler prototype

### Fix

- **ui**: fix full-width header and stable result panels
- **ui**: fix action button layout in single column

### Refactor

- restructure into telekom_profiler package with Ollama
