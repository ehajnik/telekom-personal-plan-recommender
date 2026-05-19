# Changelog

## Unreleased

### Added

- Centralized business thresholds in `telekom_profiler/config/thresholds.py`
- Typed `CustomerUsage` validation/clamping and `ProfileResult.to_state_dict()` for Gradio state
- `ProfilerEngine` fallback providers when Ollama fails (`OLLAMA_FALLBACK_ON_ERROR`)
- Ollama tuning: `OLLAMA_TIMEOUT`, `OLLAMA_NUM_PREDICT`
- UI scoring summary panel and inference mode label
- Structured logging (`telekom_profiler/logging_config.py`)
- Documentation: ADR, Ollama runbook, expanded `docs/`
- Dev tooling: ruff, mypy, GitHub Actions CI

### Changed

- Rule-based offers bias tariffs by primary archetype from scoring
- Profile prompts require deterministic primary archetype from code scoring
- UI uses `gr.State` for profile instead of passing markdown only
- Removed duplicate root `styles/`, `data/`, `assets/` directories

### Fixed

- Gradio header width and main column stretch CSS for Gradio 6
- Engine singleton reset on app startup for fresh provider selection
