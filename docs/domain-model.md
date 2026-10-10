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
| `data_trend` | float | Data trajectory, relative change in % per year (−50 … +50) |
| `voice_trend` | float | Voice trajectory, relative change in % per year (−50 … +50) |

### 2.1 Feature classification

| Group | Fields | Used for |
|-------|--------|----------|
| Usage levels | `data_gb`, `voice_min`, `sms_count`, `roaming_days` | ML: log1p-scaled clustering features; rules mode: L1 distance on slider-normalised values |
| Trends | `data_trend`, `voice_trend` | Overlay flags, narrative, offer sizing (growth raises projected need); not clustering inputs |

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

Upstream systems should aggregate usage levels as monthly means (the ML model was trained on 12-month means) and compute trends as the annualised OLS slope relative to the mean: `slope_per_month × 12 / mean × 100`, clipped to ±50 (`ml/features.py` → `build_subscriber_features` is the reference implementation).

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

Curated anchors (`model.fixed_centroids`, human units) and profile text (`ml/profile_characteristics.py`) are mapped to trained clusters once during training. `scripts/evaluate_model.py` reports anchor drift and fails above 25 %; after a generator change, refresh anchors with `--print-anchors`.

### 3.1 Clustering features and distance metric

Clustering uses **only features computable from the six-slider input**: `log1p` of `data_gb`, `voice_min`, `sms_count`, `roaming_days` (12-month means at training time). An earlier 12-feature set mixed in imputed values (session size, active days, plan tier, countries) and classified only 76.8 % of slider-entered subscribers correctly versus 100 % now.

ML inference (`ml/inference.py`) computes nearest-centroid Euclidean distance in standardised space:

- uses `artifacts/frozen_centroids.json` + `artifacts/cluster_features.json`
- normalises by stored `scaler_scale`
- picks nearest and second-nearest labels for confidence

### 3.2 Confidence

`ml_confidence(primary, secondary)` (`ml/overlays.py`) returns `High` (ratio < 0.75), `Medium` (< 0.9) or `Low` from the primary/secondary distance ratio.

---

## 4. Overlays

Overlays are cross-cutting tags applied in addition to the primary profile.

| Mode | Condition | Overlay label |
|------|-----------|---------------|
| ML (`ml/overlays.py`, thresholds in `app_config.yaml` → `runtime.overlay_thresholds`) | data trend ≥ +10 % / ≤ −10 % per year | Data appetite growing / shrinking |
| ML | voice trend ≤ −10 % per year | Voice declining → data migration |
| ML | roaming +2 days/month over the year | Roaming increasing |
| ML | second distance < 1.3 × primary distance | Mixed profile |
| Rules (`domain/archetypes.py`, thresholds in `config/thresholds.py`) | data trend > +10 % per year | Data growth |
| Rules | voice trend < −10 % per year | Voice decline |
| Rules | roaming ≥ 8 days/month | Roaming-heavy |
| Rules | data < 12 GB, voice < 300 min, roaming ≤ 2 days | Budget-sensitive |

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
| `source` | `rule_based`, `ml_kmeans`, `litellm/<provider>` (e.g. `litellm/ollama`), `rule_based_fallback`, or custom provider tag |
| `is_placeholder` | Derived from markdown prefix; blocks offer generation |
| `to_state_dict()` / `from_state_dict()` | Gradio session serialisation |

### 6.2 Generation paths

| Path | Profile | Offer |
|------|---------|-------|
| Rules mode | `render_profile_report()` | `render_offer_report()` → `offers.recommend()` |
| ML mode | `render_ml_profile_report()` (customer usage vs profile reference) | same rule engine |
| LLM | `build_profile_prompt()` → LiteLLM | `build_offer_prompt()` (incl. usage + rule-engine sizing) → LiteLLM |

### 6.3 Offer sizing rule

`domain/offers.recommend()` picks the **cheapest tariff whose data allowance covers** `data_gb × (1 + max(0, data_trend)/100) × 1.10`. The primary profile sets the channel and floor: light profiles get prepaid when it fits (≤ 80 GB, < 8 roaming days); travel-heavy customers get at least MagentaMobil L for the 25 GB/year non-EU volume; everyone else gets postpaid with a prepaid alternative when one fits. Travel & Surf passes are only suggested from 8 roaming days/month. PlusKarte is an agent question, never inferred from data volume.

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

In ML mode, templates come from `artifacts/profile_characteristics.json` (`slider_defaults` = rounded anchors; unit tests verify each template is classified as its own profile). In rules mode they come from `ui.profiles` in `app_config.yaml`. Production feeds should populate `CustomerUsage` directly from systems of record.

Note: names like `Streamer`/`Chatterbox` are legacy rule-mode presets used when ML artifacts are unavailable or when `PROFILER_MODE=rules` is selected. They are not the canonical ML taxonomy.

---

## 9. Reference data files

| File | Consumed by |
|------|-------------|
| `data/consumer_archetypes.md` | Profile prompt — profile descriptions (rules mode / no artifacts) |
| `data/plans_and_options.md` | Offer prompt — full catalogue with SKUs and sources |
| `data/tariffs_private.md` | Offer prompt fallback — catalogue summary |
| `domain/catalog.py` | Rule-based offer engine (structured; kept in sync with the markdown by `tests/test_catalog.py`) |

For production, replace static files with synchronised catalogue APIs or scheduled exports; keep the same semantic sections expected by prompt builders.
