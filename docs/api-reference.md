# API reference

Stable Python surface for programmatic integration, automated tests, and headless services. Internal UI code may import additional modules; integrators should depend only on symbols listed here unless coordinated with the owning team.

---

## 1. Package entry

```python
import telekom_profiler

telekom_profiler.__version__   # e.g. "0.3.0" (from pyproject.toml / install metadata)
telekom_profiler.create_demo() # gradio.Blocks
telekom_profiler.main()        # configure logging, reset engine, launch UI
```

---

## 2. Services (`telekom_profiler.services`)

### 2.1 Functions

#### `profile_customer(data, *, engine=None) -> str`

Returns profile markdown. Delegates to `ProfilerEngine.profile()`. Uses Ollama when enabled.

For scoring metadata and `source`, use `profile_customer_structured`.

#### `profile_customer_structured(data, *, engine=None) -> ProfileResult`

**Preferred integration entry.** Returns typed `ProfileResult` including `scoring` and `source`.

```python
from telekom_profiler.services import profile_customer_structured

result = profile_customer_structured({"data_gb": 40, ...})
```

#### `recommend_offer(profile, data, *, engine=None) -> str`

Returns offer markdown.

| `profile` type | Behaviour |
|----------------|-----------|
| `ProfileResult` | Preferred; passes full context to providers |
| `str` | Legacy markdown; still supported |

`data` may be `CustomerUsage` or a mapping. Caller must ensure profile is not a placeholder.

---

### 2.2 `ProfilerEngine`

```python
from telekom_profiler.services import ProfilerEngine

engine = ProfilerEngine(profile_provider=None, offer_provider=None)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `profile` | `(usage: CustomerUsage \| Mapping) -> ProfileResult` | Profile with scoring |
| `recommend` | `(profile: ProfileResult \| str, usage: CustomerUsage \| Mapping) -> str` | Offer markdown |

Construct with custom providers for production backends. Default providers are selected from environment flags.

#### `get_engine() -> ProfilerEngine`

Process-wide singleton used by the UI and convenience functions. Call `reset_engine()` after environment changes in long-running tests.

---

### 2.3 Protocols (`services.protocols`)

#### `ProfileProvider`

```python
def profile(self, usage: CustomerUsage) -> ProfileResult: ...
```

#### `OfferProvider`

```python
def recommend(self, profile: ProfileResult, usage: CustomerUsage) -> str: ...
```

---

### 2.4 Built-in providers (`services.providers`, `services.fallback`)

| Class | `source` (typical) | Description |
|-------|-------------------|-------------|
| `RuleBasedProfileProvider` | `rule_based` | Deterministic report + scoring |
| `OllamaProfileProvider` | `ollama` | LLM narrative + scoring |
| `FallbackProfileProvider` | `rule_based_fallback` | Ollama with rule fallback |
| `RuleBasedOfferProvider` | `rule_based` | Threshold catalogue |
| `OllamaOfferProvider` | `ollama` | LLM offer narrative |
| `FallbackOfferProvider` | (via rules) | Ollama with rule fallback |

Factory functions `default_profile_provider()` and `default_offer_provider()` honour `OLLAMA_ENABLED` and `OLLAMA_FALLBACK_ON_ERROR`.

---

## 3. Domain (`telekom_profiler.domain`)

### 3.1 Models

| Class | Description |
|-------|-------------|
| `CustomerUsage` | Six usage fields; `from_mapping()`, `as_dict()`, `defaults()` |
| `ArchetypeScore` | `name: str`, `distance: float` |
| `ScoringResult` | `primary`, `secondary`, `all_distances`, `overlays`, `confidence` |
| `ProfileResult` | `markdown`, `usage`, `scoring`, `source`, `is_placeholder`, `to_state_dict()`, `from_state_dict()` |

### 3.2 Functions

| Function | Returns |
|----------|---------|
| `compute_archetype_distances(data)` | `list[tuple[str, float]]` ascending by distance |
| `compute_overlays(data)` | `list[str]` |
| `build_scoring_result(usage)` | `ScoringResult` |
| `render_profile_report(data)` | Profile markdown (rule-based) |
| `render_offer_report(profile_text, data, *, scoring=None)` | Offer markdown (rule-based) |
| `usage_slider_maxima()` | `dict[str, float]` |

### 3.3 Constants

- `ARCHETYPE_NAMES` — five archetype identifiers  
- `ARCHETYPE_CENTROIDS` — name → `(data_gb, voice_min, sms_count, roaming_days)`  

---

## 4. Prompts (`telekom_profiler.prompts`)

| Function | Description |
|----------|-------------|
| `build_profile_prompt(data)` | Filled profile-generation prompt |
| `build_offer_prompt(customer_profile)` | Filled offer-generation prompt |
| `format_slider_features(data)` | Human-readable feature block |
| `format_centroid_distances(distances)` | Distance listing for prompts |
| `format_overlay_signals(overlays)` | Overlay listing for prompts |

---

## 5. LLM client (`telekom_profiler.llm.client`)

#### `chat_completion(user_prompt, *, temperature=0.3) -> str`

Single-turn completion against configured Ollama host and model. Raises `RuntimeError` on transport or API errors.

---

## 6. Configuration modules

### `telekom_profiler.config` (sliders)

`USAGE_SLIDERS`, `TREND_SLIDERS`, `SLIDER_KEYS`, `PROFILES`, message constants, `CUSTOM_PROFILE`.

### `telekom_profiler.config.ollama_settings`

`OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_ENABLED`, `OLLAMA_TIMEOUT`, `OLLAMA_NUM_PREDICT`, `OLLAMA_FALLBACK_ON_ERROR`, `llm_enabled()`, `fallback_on_error()`.

### `telekom_profiler.config.thresholds`

Business thresholds for overlays and offer selection (import specific constants as needed).

---

## 7. Paths (`telekom_profiler.paths`)

| Name | Resolves to |
|------|-------------|
| `PACKAGE_ROOT` | Installed `telekom_profiler/` directory |
| `ASSETS_DIR` | Brand assets |
| `DATA_DIR` | Reference markdown |
| `PROMPT_TEMPLATES_DIR` | Prompt templates |
| `THEME_DIR` | CSS and Gradio theme helpers |

---

## 8. UI (`telekom_profiler.ui.demo`)

| Function | Description |
|----------|-------------|
| `create_demo()` | Construct `gr.Blocks` application |
| `main()` | Launch with Telekom theme and CSS |

Presentation hooks (`elem_classes`) are documented in the root [README](../README.md#repository-structure). Prefer `services` API for non-UI integrations.

---

## 9. Versioning policy

Breaking changes to symbols in this reference require:

1. Version bump in `pyproject.toml`  
2. `CHANGELOG.md` entry  
3. Coordination with downstream integration teams  

Additive fields on dataclasses are non-breaking; renaming or removing fields is breaking.
