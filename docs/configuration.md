# Configuration reference

Central reference for runtime settings, UI parameters, and packaged assets. Environment variables are loaded at import time from `.env` in the repository root via `python-dotenv` (`config/ollama_settings.py`, `config/profiler_settings.py`).

---

## 1. Environment variables

Copy the template and adjust for your workstation or deployment namespace:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API base URL (no trailing slash) |
| `OLLAMA_MODEL` | `ollama/qwen2.5:7b` (falls back to `llm.default_model` in `app_config.yaml`) | Startup model id for LiteLLM (`ollama/` prefix added if missing); must be listed in `llm.models`, otherwise the first listed model is used |
| `LITELLM_API_BASE` | _(empty)_ | Optional custom base URL for non-Ollama LiteLLM providers/proxies |
| `OLLAMA_ENABLED` | `true` | When `false`, selects rule-based profile and offer providers |
| `OLLAMA_TIMEOUT` | `180` | LiteLLM request timeout (seconds); raise for larger models on CPU |
| `OLLAMA_NUM_PREDICT` | `6144` | Maximum completion tokens per request; repair retries use 1.5× this budget |
| `OLLAMA_FALLBACK_ON_ERROR` | `true` | On LLM failure, delegate to rule-based providers |
| `OPENAI_API_KEY` | _(empty)_ | Required for `openai/*` model ids (paid OpenAI account required) |
| `ANTHROPIC_API_KEY` | _(empty)_ | Required for `anthropic/*` model ids (paid Anthropic account required). `temperature` is not sent for Anthropic models — current Claude models reject sampling parameters |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | _(empty)_ | Required for `gemini/*` model ids (Google AI Studio/Vertex billing may apply) |
| `LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `WARNING`, `ERROR`, …) |
| `PROFILER_CONFIG` | `<repo>/app_config.yaml` | Path to `app_config.yaml` (needed for non-editable installs; artifacts are still read from `<repo>/artifacts`) |
| `PROFILER_MODE` | `auto` | `auto` uses trained K-Means when `artifacts/` is complete, otherwise rule-based archetypes; `ml` forces ML (errors if artifacts are missing); `rules` pins the legacy archetype scoring (used by CI and the unit-test gate) |

Operational detail and troubleshooting: [Ollama runbook](runbook-ollama.md). ML pipeline outputs are detailed in [Development § 4](development.md#4-ml-profiling-pipeline-poc).

### 1.1 CI and offline development

```env
OLLAMA_ENABLED=false
```

No Ollama process is required. The UI displays **Inference: rule-based**. This is the recommended default for automated pipelines.

### 1.2 Strict LLM mode (debugging)

```env
OLLAMA_ENABLED=true
OLLAMA_FALLBACK_ON_ERROR=false
```

Failures surface in the UI instead of silently falling back. Use only when validating LLM integration.

### 1.3 CPU-only workstations (no dedicated GPU)

The repository defaults assume **LiteLLM routed to local Ollama**. Archetype scoring remains deterministic in code or ML; the LLM only generates narrative markdown.

| Goal | Suggested `OLLAMA_MODEL` | Notes |
|------|--------------------------|-------|
| Default quality | `ollama/qwen2.5:7b` | Matches `.env.example`; stronger narratives than 1B/3B class models |
| Similar quality alternative | `ollama/llama3.1:8b` | Good general reasoning; comparable hardware profile |
| Highest local quality | `ollama/mistral-nemo:12b` | Raise `OLLAMA_TIMEOUT`; needs ~16 GB RAM and benefits from pre-warm |
| No local LLM | — | `OLLAMA_ENABLED=false` (recommended for CI) |

Keep `OLLAMA_FALLBACK_ON_ERROR=true` on laptops so timeouts fall back to rule-based providers. For `mistral-nemo:12b`, raise `OLLAMA_TIMEOUT` and ensure RAM headroom.

Operational detail: [Ollama runbook — CPU-only](runbook-ollama.md#8-cpu-only-workstations-no-dedicated-gpu).

---

## 2. Root YAML configuration

Primary runtime configuration is defined in the repository-root `app_config.yaml` and loaded through `telekom_profiler/config/app_config.py`.

| Section | Purpose |
|---------|---------|
| `model` | Fixed profile count (`n_profiles`), labels, emoji, clustering features (`log_*` usage levels) and curated anchors (`fixed_centroids`, human units) |
| `runtime` | Descriptive slider-to-feature imputation (not used for clustering) and ML overlay thresholds (trend units: % per year) |
| `training` | One-time training defaults (`min_silhouette`, random seed, offline flag) |
| `llm` | Hardcoded UI model dropdown options and default model |
| `ui` | UI title, slider bounds/defaults, and template presets |

`telekom_profiler/config/sliders.py` now resolves slider and template values from `app_config.yaml`.

If you change the synthetic generator or training dataset:

1. `python scripts/evaluate_model.py --print-anchors` → paste into `app_config.yaml` → `model.fixed_centroids`
2. Update template slider positions (rounded anchors) and signatures in `telekom_profiler/ml/profile_characteristics.py`
3. Retrain (`scripts/subscriber_profiling.py`) and run `scripts/evaluate_model.py` — it fails on accuracy < 90 %, a misclassified template, or anchor drift > 25 %.

This project is designed for frozen runtime inference, not continuous retraining.

## 3. Slider and preset configuration

### 3.1 Usage sliders

| Key | Label | Min | Max | Default |
|-----|-------|-----|-----|---------|
| `data_gb` | Monthly data (GB) | 0 | 150 | 30 |
| `voice_min` | Voice minutes | 0 | 3000 | 400 |
| `sms_count` | SMS count | 0 | 500 | 50 |
| `roaming_days` | Roaming days / month | 0 | 30 | 2 |

### 3.2 Trend sliders

| Key | Label | Min | Max | Default |
|-----|-------|-----|-----|---------|
| `data_trend` | Data trend (% / year) | −50 | 50 | 5 |
| `voice_trend` | Voice trend (% / year) | −50 | 50 | 0 |

Trends are relative changes in % per year. They influence overlay flags, narrative and offer sizing; they are not clustering inputs (see [Domain model](domain-model.md)).

### 3.3 UI messages and guards

| Constant | Purpose |
|----------|---------|
| `MSG_RUN_PROFILE` | Initial profile panel placeholder |
| `MSG_GENERATE_OFFER` | Initial offer panel placeholder |
| `MSG_AFTER_PROFILE` | Hint after successful profile run |
| `MSG_RUN_PROFILE_FIRST` | Error when offer is requested without profile |
| `PLACEHOLDER_PREFIX` | `_` — marks non-result content; offer step is blocked |

### 3.4 Profile templates (presets)

`PROFILES` maps template names to partial slider overrides. Keys must be a subset of `SLIDER_KEYS`. The `— Custom —` entry applies no override.

```python
PROFILES["Workshop — Streamer"] = {
    "data_gb": 120,
    "voice_min": 300,
    # omit keys that should retain current slider values
}
```

Presets are already YAML-backed through `app_config.yaml`.

---

## 4. Business thresholds

Centralised in `telekom_profiler/config/thresholds.py`:

- Rules-mode overlay activation (data growth, voice decline, roaming-heavy, budget-sensitive)
- Offer sizing: `OFFER_DATA_HEADROOM` (1.10), `OFFER_ROAMING_ADDON_DAYS` (8), `OFFER_LONG_STAY_ROAMING_DAYS` (14)

Tariff prices and allowances live in `telekom_profiler/domain/catalog.py` (rules) and `telekom_profiler/data/plans_and_options.md` (LLM); `tests/test_catalog.py` keeps them identical.

Modify thresholds in one place to keep rule-based profiling, scoring overlays, and offers aligned. Document changes in `CHANGELOG.md`.

---

## 5. Gradio launch parameters

Configured in `telekom_profiler/ui/demo.py` → `main()`:

```python
create_demo().launch(theme=DT_THEME, css=DT_CSS, favicon_path=...)
```

For shared or hosted demos (non-production):

```python
demo.launch(
    theme=DT_THEME,
    css=DT_CSS,
    server_name="0.0.0.0",
    server_port=7860,
    auth=("demo", "<secret>"),  # replace with corporate SSO in production
)
```

Production hosting requirements: [Deployment](deployment.md).

---

## 6. Packaged assets

Declared in `pyproject.toml` under `[tool.setuptools.package-data]`:

| Pattern | Content |
|---------|---------|
| `prompts/templates/*.md` | LLM prompt templates |
| `data/*.md` | Profile and tariff reference (`plans_and_options.md`, `tariffs_private.md`, `consumer_archetypes.md`) |
| `ui/theme/*.css` | Telekom theme overrides |
| `assets/*` | Brand assets (e.g. logo SVG) |

Runtime resolution uses `telekom_profiler.paths` (`PACKAGE_ROOT`, `DATA_DIR`, `PROMPT_TEMPLATES_DIR`, `THEME_DIR`, `ASSETS_DIR`).

---

## 7. Configuration ownership (recommended)

| Area | Suggested owner | Change frequency |
|------|-----------------|------------------|
| `.env` / secrets | Platform engineering | Per environment |
| Sliders and presets | Product / campaign | Per workshop or segment refresh |
| Thresholds | Segmentation / pricing | Per policy change |
| Prompt templates | AI governance / data science | Per model policy |
| Reference markdown | Product management | Per catalogue or archetype update |
