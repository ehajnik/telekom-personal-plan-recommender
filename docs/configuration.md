# Configuration reference

Central reference for runtime settings, UI parameters, and packaged assets. Environment variables are loaded at import time from `.env` in the repository root via `python-dotenv` (`config/ollama_settings.py`).

---

## 1. Environment variables

Copy the template and adjust for your workstation or deployment namespace:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API base URL (no trailing slash) |
| `OLLAMA_MODEL` | `llama3.2` | Model tag; must exist on the host (`ollama pull`) |
| `OLLAMA_ENABLED` | `true` | When `false`, selects rule-based profile and offer providers |
| `OLLAMA_TIMEOUT` | `180` | HTTP client timeout (seconds); higher on CPU-only hosts |
| `OLLAMA_NUM_PREDICT` | `512` | Maximum completion tokens per request |
| `OLLAMA_FALLBACK_ON_ERROR` | `true` | On LLM failure, delegate to rule-based providers |
| `LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `WARNING`, `ERROR`, …) |

Operational detail and troubleshooting: [Ollama runbook](runbook-ollama.md).

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

The repository defaults assume **CPU inference** via local Ollama. Archetype scoring remains deterministic in code or ML; the LLM only generates narrative markdown.

| Goal | Suggested `OLLAMA_MODEL` | Notes |
|------|--------------------------|-------|
| Default balance | `llama3.2` | Matches `.env.example`; `ollama pull llama3.2` |
| Faster / less RAM | `llama3.2:1b`, `qwen2.5:3b`, `phi3:mini` | Set `OLLAMA_MODEL` accordingly after `ollama pull` |
| No local LLM | — | `OLLAMA_ENABLED=false` (recommended for CI) |

Keep `OLLAMA_FALLBACK_ON_ERROR=true` on laptops so timeouts fall back to rule-based providers. Avoid 7B+ models (for example `llama3:latest`) on CPU-only hosts.

Operational detail: [Ollama runbook — CPU-only](runbook-ollama.md#8-cpu-only-workstations-no-dedicated-gpu).

---

## 2. Slider and preset configuration

Defined in `telekom_profiler/config/sliders.py`. Changes to maxima propagate to archetype normalisation via `usage_slider_maxima()`.

### 2.1 Usage sliders

| Key | Label | Min | Max | Default |
|-----|-------|-----|-----|---------|
| `data_gb` | Monthly data (GB) | 0 | 150 | 30 |
| `voice_min` | Voice minutes | 0 | 3000 | 400 |
| `sms_count` | SMS count | 0 | 500 | 50 |
| `roaming_days` | Roaming days / month | 0 | 30 | 2 |

### 2.2 Trend sliders

| Key | Label | Min | Max | Default |
|-----|-------|-----|-----|---------|
| `data_trend` | Data trend | −50 | 50 | 5 |
| `voice_trend` | Voice trend | −50 | 50 | 0 |

Trends influence overlay flags and narrative context; they are not archetype clustering inputs unless a downstream model defines otherwise (see [Domain model](domain-model.md)).

### 2.3 UI messages and guards

| Constant | Purpose |
|----------|---------|
| `MSG_RUN_PROFILE` | Initial profile panel placeholder |
| `MSG_GENERATE_OFFER` | Initial offer panel placeholder |
| `MSG_AFTER_PROFILE` | Hint after successful profile run |
| `MSG_RUN_PROFILE_FIRST` | Error when offer is requested without profile |
| `PLACEHOLDER_PREFIX` | `_` — marks non-result content; offer step is blocked |

### 2.4 Profile templates (presets)

`PROFILES` maps template names to partial slider overrides. Keys must be a subset of `SLIDER_KEYS`. The `— Custom —` entry applies no override.

```python
PROFILES["Workshop — Streamer"] = {
    "data_gb": 120,
    "voice_min": 300,
    # omit keys that should retain current slider values
}
```

For production, consider loading presets from configuration management (YAML/JSON) rather than hard-coding in source.

---

## 3. Business thresholds

Centralised in `telekom_profiler/config/thresholds.py`:

- Overlay activation (data growth, voice decline, roaming-heavy, budget-sensitive)
- Offer catalogue selection biases

Modify thresholds in one place to keep rule-based profiling, scoring overlays, and offers aligned. Document changes in `CHANGELOG.md`.

---

## 4. Gradio launch parameters

Configured in `telekom_profiler/ui/demo.py` → `main()`:

```python
create_demo().launch(theme=DT_THEME, css=DT_CSS)
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

## 5. Packaged assets

Declared in `pyproject.toml` under `[tool.setuptools.package-data]`:

| Pattern | Content |
|---------|---------|
| `prompts/templates/*.md` | LLM prompt templates |
| `data/*.md` | Archetype and tariff reference |
| `ui/theme/*.css` | Telekom theme overrides |
| `assets/*` | Brand assets (e.g. logo SVG) |

Runtime resolution uses `telekom_profiler.paths` (`PACKAGE_ROOT`, `DATA_DIR`, `PROMPT_TEMPLATES_DIR`, `THEME_DIR`, `ASSETS_DIR`).

---

## 6. Configuration ownership (recommended)

| Area | Suggested owner | Change frequency |
|------|-----------------|------------------|
| `.env` / secrets | Platform engineering | Per environment |
| Sliders and presets | Product / campaign | Per workshop or segment refresh |
| Thresholds | Segmentation / pricing | Per policy change |
| Prompt templates | AI governance / data science | Per model policy |
| Reference markdown | Product management | Per catalogue or archetype update |
