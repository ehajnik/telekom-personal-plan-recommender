# Domain model

Business and technical specification of data contracts used across the Private Customer Profiler. This document is the authoritative reference for integration teams implementing CRM, billing, or segmentation feeds.

---

## 1. Overview

The domain layer (`telekom_profiler.domain`) defines:

- **Input:** `CustomerUsage` — normalised usage snapshot  
- **Scoring:** `ScoringResult` — deterministic archetype and overlay metadata  
- **Output:** `ProfileResult` — profile markdown plus scoring; offer output as markdown string  

Scoring is always computed in application code ([ADR 001](adr/001-scoring-in-code.md)), independent of LLM narrative.

---

## 2. Customer usage snapshot

`CustomerUsage` (`domain/models.py`) is the canonical input for profiling and offer generation.

| Field | Type | Role |
|-------|------|------|
| `data_gb` | float | Monthly mobile data (GB) |
| `voice_min` | float | Voice minutes per month |
| `sms_count` | float | SMS count per month |
| `roaming_days` | float | Days abroad per month |
| `data_trend` | float | Data trajectory (−50 … +50) |
| `voice_trend` | float | Voice trajectory (−50 … +50) |

### 2.1 Feature classification

| Group | Fields | Used for |
|-------|--------|----------|
| Usage levels | `data_gb`, `voice_min`, `sms_count`, `roaming_days` | Archetype distance (L1 on normalised values) |
| Trends | `data_trend`, `voice_trend` | Overlay flags and narrative; not clustering inputs in the current model |

### 2.2 Construction and validation

```python
from telekom_profiler.domain import CustomerUsage

usage = CustomerUsage.from_mapping({"data_gb": 95, ...}, clamp=True)
usage.as_dict()  # serialisation for prompts and APIs
```

When `clamp=True`, values are bounded to slider minima/maxima from configuration, preventing out-of-range UI or API input from distorting scoring.

### 2.3 JSON contract (integration)

```json
{
  "data_gb": 95.0,
  "voice_min": 200.0,
  "sms_count": 30.0,
  "roaming_days": 8.0,
  "data_trend": 15.0,
  "voice_trend": -5.0
}
```

Upstream systems should document aggregation rules (e.g. three-month average for usage levels, month-over-month delta mapped to trend scale).

---

## 3. ML profile taxonomy

Runtime ML mode uses five fixed labels from `app_config.yaml`:

| Label | Typical signature |
|-------|-------------------|
| **Light / occasional user** | Low baseline data/voice with minimal roaming |
| **Streaming & data-heavy** | Very high data and session intensity |
| **Voice-centric** | High voice minutes with low-to-moderate data |
| **Roaming / travel-heavy** | Frequent roaming and multiple countries visited |
| **Broad usage profile** | High overall engagement with mixed usage intensity |

Centroids and profile metadata are hardcoded in root configuration and profile characteristics modules, then mapped once during training.
If you retrain on a new dataset, you must refresh both hardcoded layers and corresponding frozen artifacts to avoid drift.

### 3.1 Distance metric

ML inference (`ml/inference.py`) computes nearest-centroid distance over configured cluster features in scaled space:

- uses `artifacts/frozen_centroids.json` + `artifacts/cluster_features.json`
- normalises by stored `scaler_scale`
- picks nearest and second-nearest labels for confidence

### 3.2 Confidence

`_confidence(primary, secondary)` in ML inference returns `High`, `Medium`, or `Low` from the primary/secondary distance ratio.

---

## 4. Overlays

Overlays are cross-cutting tags applied in addition to the primary archetype (`compute_overlays`, thresholds in `config/thresholds.py`):

| Condition (conceptual) | Overlay label |
|------------------------|---------------|
| Strong positive data trend | Data growth |
| Strong negative voice trend | Voice decline |
| Elevated roaming days | Roaming-heavy |
| Low usage across key dimensions | Budget-sensitive |

Overlays appear in rule-based profile section 2, in prompt context, and in the UI scoring summary.

---

## 5. Scoring result

`ScoringResult` aggregates deterministic segmentation metadata:

| Member | Description |
|--------|-------------|
| `primary`, `secondary` | `ArchetypeScore(name, distance)` |
| `all_distances` | Full ranked list |
| `overlays` | Active overlay strings |
| `confidence` | `High` / `Medium` / `Low` |

Built via `build_scoring_result(usage)` and attached to every `ProfileResult` from built-in providers. Downstream analytics should key off `scoring.primary.name` rather than parsing profile markdown.

---

## 6. Profile and offer artefacts

| Artefact | Type | Contents |
|----------|------|----------|
| Profile | `ProfileResult` | `markdown`, `usage`, `scoring`, `source` |
| Offer | `str` (markdown) | Tariff tables, add-ons, agent next steps |

### 6.1 Profile result

| Field | Values / notes |
|-------|----------------|
| `source` | `rule_based`, `ollama`, `rule_based_fallback`, or custom provider tag |
| `is_placeholder` | Derived from markdown prefix; blocks offer generation |
| `to_state_dict()` / `from_state_dict()` | Gradio session serialisation |

### 6.2 Generation paths

| Path | Profile | Offer |
|------|---------|-------|
| Rule-based | `render_profile_report()` | `render_offer_report()` (may use `scoring` for tariff bias) |
| LLM | `build_profile_prompt()` → Ollama | `build_offer_prompt()` → Ollama |

---

## 7. LLM narrative vs deterministic scoring

The profile prompt includes `required_primary` and `required_confidence` from code scoring so the narrative aligns with audit metadata. The model may still vary wording in non-primary sections.

| Requirement | Approach |
|-------------|----------|
| Strict segment ID for CRM | Use `result.scoring.primary.name` |
| Agent-readable explanation | Use `result.markdown` |
| Governance comparison | Log scoring alongside LLM `source` |

Rule-based `render_profile_report()` always uses `distances[0]` as the stated primary archetype.

---

## 8. UI profile templates

UI templates are defined under `ui.profiles` in root `app_config.yaml` and resolved through `config/sliders.py`. Presets are aligned with fixed profile behavior for demonstration; production feeds should populate `CustomerUsage` directly from systems of record.

Note: names like `Streamer`/`Chatterbox` are legacy rule-mode presets used when ML artifacts are unavailable or when `PROFILER_MODE=rules` is selected. They are not the canonical ML taxonomy.

---

## 9. Reference data files

| File | Consumed by |
|------|-------------|
| `data/consumer_archetypes.md` | Profile prompt — archetype descriptions |
| `data/tariffs_private.md` | Offer prompt — prototype tariff catalogue |

For production, replace static files with synchronised catalogue APIs or scheduled exports; keep the same semantic sections expected by prompt builders.
