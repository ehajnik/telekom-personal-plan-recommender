# Domain model

## Customer usage snapshot

`CustomerUsage` (`telekom_profiler.domain.models`) is the canonical input for profiling and offers.

| Field | Type | Role |
|-------|------|------|
| `data_gb` | float | Monthly mobile data (GB) |
| `voice_min` | float | Voice minutes per month |
| `sms_count` | float | SMS count per month |
| `roaming_days` | float | Days abroad per month |
| `data_trend` | float | Data trajectory (−50 … +50) |
| `voice_trend` | float | Voice trajectory (−50 … +50) |

**Usage features** (`data_gb`, `voice_min`, `sms_count`, `roaming_days`) feed archetype distance calculation.

**Trends** (`data_trend`, `voice_trend`) drive **overlay flags** and narrative text; they are documented as *not* clustering inputs in the UI and prompts.

```python
from telekom_profiler.domain import CustomerUsage

usage = CustomerUsage.from_mapping({"data_gb": 95, ...})
usage.as_dict()  # legacy dict for prompts
```

## Consumer archetypes

Five core B2C usage archetypes are defined in `ARCHETYPE_CENTROIDS` (`domain/archetypes.py`). Each centroid is a tuple `(data_gb, voice_min, sms_count, roaming_days)` representing a typical subscriber.

| Archetype | Typical signature |
|-----------|-------------------|
| **Streamer** | Very high data, moderate voice, low roaming |
| **Chatterbox** | Low data, very high voice |
| **Essential** | Low across all usage dimensions |
| **Roamer** | Elevated roaming days |
| **Messenger** | High SMS, moderate data |

### Distance metric

Usage values are **normalized** by slider maxima (from `USAGE_SLIDERS`), then compared to each centroid using **Manhattan (L1) distance**. Lower distance ⇒ closer match.

```python
from telekom_profiler.domain import compute_archetype_distances

ranked = compute_archetype_distances(usage.as_dict())
primary_name, primary_distance = ranked[0]
```

### Confidence

`confidence_label(primary, secondary)` returns `High`, `Medium`, or `Low` based on the gap between the best and second-best distances. Used in rule-based profiles and available on `ScoringResult`.

## Overlays

Overlays are cross-cutting tags applied on top of the primary archetype (`compute_overlays`):

| Condition | Overlay |
|-----------|---------|
| `data_trend > 10` | Data growth |
| `voice_trend < -10` | Voice decline |
| `roaming_days >= 8` | Roaming-heavy |
| Low data + low voice + low roaming | Budget-sensitive |

Overlays appear in prompts and rule-based profile section 2.

## Scoring result

`ScoringResult` bundles deterministic outputs:

- `primary`, `secondary` — `ArchetypeScore(name, distance)`
- `all_distances` — full ranking
- `overlays` — active overlay strings
- `confidence` — High / Medium / Low

Built via `build_scoring_result(usage)`; attached to every `ProfileResult` from built-in providers.

## Profile and offer artefacts

| Type | Contents |
|------|----------|
| `ProfileResult` | `markdown`, `usage`, optional `scoring`, `source` (`rule_based` / `ollama`) |
| Offer output | Markdown string (tariff tables, add-ons, agent next steps) |

Rule-based generators: `render_profile_report()`, `render_offer_report()`.

LLM generators: `build_profile_prompt()` + `build_offer_prompt()` → Ollama.

## Profile templates (UI presets)

`PROFILES` in `config/sliders.py` maps template names to partial slider overrides. Presets align with archetype centroids for demo scenarios. `— Custom —` applies no override.

## Reference data

| File | Used by |
|------|---------|
| `data/consumer_archetypes.md` | Profile prompt — archetype descriptions |
| `data/tariffs_private.md` | Offer prompt — prototype tariff catalogue |

Replace these files (or load from API) for production catalogue alignment.

## LLM vs deterministic primary archetype

The prompt states centroid distances are **indicative only**. The LLM may choose wording that does not exactly match `distances[0]`. For strict alignment, post-process LLM output or constrain the model (e.g. require primary = `{top_archetype}` in the template).

Rule-based `render_profile_report()` always uses `distances[0]` as primary.
