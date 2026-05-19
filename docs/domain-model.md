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

## 3. Consumer archetypes

Five B2C usage archetypes are defined by centroids in `ARCHETYPE_CENTROIDS` (`domain/archetypes.py`). Each centroid is `(data_gb, voice_min, sms_count, roaming_days)`.

| Archetype | Typical signature |
|-----------|-------------------|
| **Streamer** | Very high data, moderate voice, low roaming |
| **Chatterbox** | Low data, very high voice |
| **Essential** | Low usage across dimensions |
| **Roamer** | Elevated roaming days |
| **Messenger** | High SMS, moderate data |

### 3.1 Distance metric

Usage values are normalised by slider maxima (`usage_slider_maxima()`), then compared to each centroid using **Manhattan (L1) distance**. The archetype with the lowest distance is the nearest match.

```python
from telekom_profiler.domain import compute_archetype_distances

ranked = compute_archetype_distances(usage.as_dict())
primary_name, primary_distance = ranked[0]
```

### 3.2 Confidence

`confidence_label(primary, secondary)` returns `High`, `Medium`, or `Low` based on the separation between the first and second ranked archetypes. Exposed on `ScoringResult.confidence` and injected into LLM prompts as `required_confidence`.

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

`PROFILES` in `config/sliders.py` maps template names to partial slider overrides for workshops and UAT. Presets are aligned with archetype centroids for demonstration; production feeds should populate `CustomerUsage` directly from systems of record.

---

## 9. Reference data files

| File | Consumed by |
|------|-------------|
| `data/consumer_archetypes.md` | Profile prompt — archetype descriptions |
| `data/tariffs_private.md` | Offer prompt — prototype tariff catalogue |

For production, replace static files with synchronised catalogue APIs or scheduled exports; keep the same semantic sections expected by prompt builders.
