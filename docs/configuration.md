# Configuration

## Environment variables

Loaded from `.env` at project root via `python-dotenv` (`config/ollama_settings.py`).

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API base URL (no trailing slash) |
| `OLLAMA_MODEL` | `llama3.2` | Model tag; must exist locally (`ollama pull`) |
| `OLLAMA_ENABLED` | `true` | `false` forces rule-based profile and offer |
| `OLLAMA_TIMEOUT` | `120` | Client timeout in seconds |
| `OLLAMA_NUM_PREDICT` | `1024` | Max tokens per completion |
| `OLLAMA_FALLBACK_ON_ERROR` | `true` | Use rule-based providers if Ollama fails |
| `LOG_LEVEL` | `INFO` | Python log level (`DEBUG`, `WARNING`, …) |

See also [Ollama runbook](runbook-ollama.md).

Copy `.env.example` to `.env` and adjust for your workstation.

```bash
cp .env.example .env
```

### Disabling Ollama (CI / offline)

```env
OLLAMA_ENABLED=false
```

No Ollama process required; all logic uses `RuleBasedProfileProvider` and `RuleBasedOfferProvider`.

## Slider and preset configuration

Defined in `telekom_profiler/config/sliders.py`.

### Usage sliders

| Key | Label | Min | Max | Default |
|-----|-------|-----|-----|---------|
| `data_gb` | Monthly data (GB) | 0 | 150 | 30 |
| `voice_min` | Voice minutes | 0 | 3000 | 400 |
| `sms_count` | SMS count | 0 | 500 | 50 |
| `roaming_days` | Roaming days / month | 0 | 30 | 2 |

### Trend sliders

| Key | Label | Min | Max | Default |
|-----|-------|-----|-----|---------|
| `data_trend` | Data trend | −50 | 50 | 5 |
| `voice_trend` | Voice trend | −50 | 50 | 0 |

Changing maxima here automatically updates archetype normalization (`usage_slider_maxima()`).

### UI messages

| Constant | Purpose |
|----------|---------|
| `MSG_RUN_PROFILE` | Profile panel placeholder |
| `MSG_GENERATE_OFFER` | Offer panel placeholder |
| `MSG_AFTER_PROFILE` | Offer hint after profile run |
| `MSG_RUN_PROFILE_FIRST` | Error when offer clicked too early |
| `PLACEHOLDER_PREFIX` | `_` — marks non-results; offer step blocked |

### Adding a profile template

```python
PROFILES["My Persona"] = {
    "data_gb": 40,
    "voice_min": 600,
    # only keys you want to override
}
```

Keys must be a subset of `SLIDER_KEYS`.

## Gradio launch options

Configured in `telekom_profiler/ui/demo.py` → `main()`:

```python
create_demo().launch(theme=DT_THEME, css=DT_CSS)
```

For shared demos, consider:

```python
demo.launch(
    theme=DT_THEME,
    css=DT_CSS,
    server_name="0.0.0.0",
    server_port=7860,
    auth=("demo", "<secret>"),  # replace with SSO in production
)
```

## Package data files

Bundled via `pyproject.toml` `[tool.setuptools.package-data]`:

- `prompts/templates/*.md`
- `data/*.md`
- `ui/theme/*.css`
- `assets/*`

Paths resolved through `telekom_profiler.paths`.
