# API reference

Public Python API for programmatic use and integration tests.

## Package entry

```python
import telekom_profiler
telekom_profiler.__version__  # "0.1.0"
telekom_profiler.create_demo()  # Gradio Blocks
telekom_profiler.main()         # launch UI
```

## Services (`telekom_profiler.services`)

### Functions

#### `profile_customer(data, *, engine=None) -> str`

Returns profile markdown. Uses Ollama when enabled.

#### `profile_customer_structured(data, *, engine=None) -> ProfileResult`

Returns typed result including `scoring` and `source`.

#### `recommend_offer(profile_text, data, *, engine=None) -> str`

Returns offer markdown. `profile_text` must not be a placeholder (`_` prefix).

### Classes

#### `ProfilerEngine(profile_provider=None, offer_provider=None)`

| Method | Description |
|--------|-------------|
| `profile(usage)` | `CustomerUsage` or dict → `ProfileResult` |
| `recommend(profile, usage)` | `ProfileResult` or str + usage → offer markdown |

#### `get_engine() -> ProfilerEngine`

Process-wide singleton with default providers.

### Protocols

#### `ProfileProvider`

```python
def profile(self, usage: CustomerUsage) -> ProfileResult: ...
```

#### `OfferProvider`

```python
def recommend(self, profile: ProfileResult, usage: CustomerUsage) -> str: ...
```

### Built-in providers (`services.providers`)

| Class | `source` | Behaviour |
|-------|----------|-----------|
| `RuleBasedProfileProvider` | `rule_based` | `render_profile_report` + scoring |
| `OllamaProfileProvider` | `ollama` | Ollama + scoring |
| `RuleBasedOfferProvider` | `rule_based` | Threshold catalogue |
| `OllamaOfferProvider` | `ollama` | Ollama + tariff markdown |

## Domain (`telekom_profiler.domain`)

### Models

| Class | Fields / methods |
|-------|------------------|
| `CustomerUsage` | Six usage fields; `from_mapping()`, `as_dict()`, `defaults()` |
| `ArchetypeScore` | `name`, `distance` |
| `ScoringResult` | `primary`, `secondary`, `all_distances`, `overlays`, `confidence` |
| `ProfileResult` | `markdown`, `usage`, `scoring`, `source`, `is_placeholder` |

### Functions

| Function | Returns |
|----------|---------|
| `compute_archetype_distances(data)` | `list[tuple[str, float]]` sorted by distance |
| `compute_overlays(data)` | `list[str]` |
| `build_scoring_result(usage)` | `ScoringResult` |
| `render_profile_report(data)` | Profile markdown |
| `render_offer_report(profile_text, data)` | Offer markdown |
| `usage_slider_maxima()` | `dict[str, float]` |

### Constants

- `ARCHETYPE_NAMES` — tuple of five archetype names
- `ARCHETYPE_CENTROIDS` — name → usage tuple

## Prompts (`telekom_profiler.prompts`)

| Function | Description |
|----------|-------------|
| `build_profile_prompt(data)` | Filled profile prompt string |
| `build_offer_prompt(customer_profile)` | Filled offer prompt string |
| `format_slider_features(data)` | Human-readable feature block |
| `format_centroid_distances(distances)` | Distance listing |
| `format_overlay_signals(overlays)` | Overlay listing |

## LLM (`telekom_profiler.llm.client`)

#### `chat_completion(user_prompt, *, temperature=0.3) -> str`

Single-turn Ollama chat. Raises `RuntimeError` on failure.

## Configuration (`telekom_profiler.config`)

Exported from `config.sliders`: `USAGE_SLIDERS`, `TREND_SLIDERS`, `SLIDER_KEYS`, `PROFILES`, messages, `CUSTOM_PROFILE`.

`config.ollama_settings`: `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_ENABLED`, `llm_enabled()`.

## Paths (`telekom_profiler.paths`)

| Constant | Path |
|----------|------|
| `PACKAGE_ROOT` | `telekom_profiler/` package dir |
| `ASSETS_DIR` | Logo SVG |
| `DATA_DIR` | Reference markdown |
| `PROMPT_TEMPLATES_DIR` | Prompt templates |
| `THEME_DIR` | CSS + theme |

## UI (`telekom_profiler.ui.demo`)

| Function | Description |
|----------|-------------|
| `create_demo()` | Construct Gradio `Blocks` |
| `main()` | Launch with Telekom theme |

CSS hooks: see README section *UI structure & CSS hooks*.
