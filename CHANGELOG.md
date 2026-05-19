# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

---

## [Unreleased]

### Added

- Centralised business thresholds in `telekom_profiler/config/thresholds.py`
- Typed `CustomerUsage` validation and clamping; `ProfileResult` state serialisation for Gradio
- Fallback providers when Ollama fails (`OLLAMA_FALLBACK_ON_ERROR`)
- Ollama tuning: `OLLAMA_TIMEOUT`, `OLLAMA_NUM_PREDICT`
- UI scoring summary panel and inference mode indicator
- Structured logging via `telekom_profiler/logging_config.py`
- Technical documentation set under `docs/` including ADR and Ollama runbook
- Developer tooling: Ruff, Mypy, GitHub Actions CI

### Changed

- Rule-based offers bias tariff selection by primary archetype from scoring
- Profile prompts require deterministic primary archetype from code scoring
- UI session uses `gr.State` with `ProfileResult` instead of markdown-only handoff
- Removed duplicate root `styles/`, `data/`, and `assets/` directories (package paths only)
- Documentation rewritten for enterprise readability and integration clarity

### Fixed

- Gradio 6 header width and main column layout CSS
- Engine singleton reset at application startup for correct provider selection

---

## [0.1.0] — initial packaged release

Baseline Gradio application with rule-based and Ollama providers, five B2C archetypes, and Telekom branding.
