# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version bumps are driven by [Commitizen](https://commitizen-tools.github.io/commitizen/) from [Conventional Commits](https://www.conventionalcommits.org/) on `main`. The canonical version lives in `pyproject.toml`; runtime reads it via `telekom_profiler.__version__`.

---


### Added

- Baseline Gradio application with rule-based and Ollama providers, five B2C archetypes, and Telekom branding

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
