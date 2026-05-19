# Integration guide

Patterns for connecting the Private Customer Profiler to Telekom Mobile systems of record, approved AI services, and downstream campaign tooling.

---

## 1. Integration principles

| Principle | Implication |
|-----------|-------------|
| Typed contracts | Prefer `CustomerUsage` and `ProfileResult` over raw markdown |
| Deterministic scoring | Use `ScoringResult` for CRM keys and analytics |
| Provider substitution | Replace rule/LLM stubs without changing the UI |
| Fail-safe inference | Respect `OLLAMA_FALLBACK_ON_ERROR` in integrated environments |

Domain definitions: [Domain model](domain-model.md). Public API: [API reference](api-reference.md).

---

## 2. Integration roadmap

| Phase | Capability | Integration surface |
|-------|------------|---------------------|
| 1 (current) | Manual sliders, prototype logic | Gradio UI + `ProfilerEngine` |
| 2 | Structured session state | `ProfileResult.to_state_dict()` in UI (implemented) |
| 3 | Enterprise segmentation | Custom `ProfileProvider` |
| 4 | Live product catalogue | Custom `OfferProvider` + PCM/BSS API |
| 5 | CRM write-back | Post-offer approval workflow (new service) |

---

## 3. API contracts

### 3.1 Input: usage vector

Use `CustomerUsage` or equivalent JSON (six numeric fields). Values should be pre-aggregated by the upstream system.

```json
{
  "data_gb": 95,
  "voice_min": 200,
  "sms_count": 30,
  "roaming_days": 8,
  "data_trend": 15,
  "voice_trend": -5
}
```

**Suggested sources:** billing averages, CDR aggregation, CRM attributes, or propensity model outputs mapped to the slider scale.

### 3.2 Output: profile

```python
from telekom_profiler.domain import CustomerUsage
from telekom_profiler.services import profile_customer_structured

usage = CustomerUsage.from_mapping(payload, clamp=True)
result = profile_customer_structured(usage.as_dict())

segment_id = result.scoring.primary.name if result.scoring else None
confidence = result.scoring.confidence if result.scoring else None
agent_narrative = result.markdown
provider = result.source
```

### 3.3 Output: offer

```python
from telekom_profiler.services import get_engine

offer_markdown = get_engine().recommend(result, usage)
```

For structured downstream systems, implement a custom `OfferProvider` returning JSON or a domain DTO, then format markdown at the edge if required.

---

## 4. Replacing the LLM backend

Implement `ProfileProvider` and/or `OfferProvider` targeting the corporate model gateway:

```python
from telekom_profiler.domain.scoring import build_scoring_result
from telekom_profiler.prompts import build_profile_prompt

class GatewayProfileProvider:
    def profile(self, usage: CustomerUsage) -> ProfileResult:
        prompt = build_profile_prompt(usage.as_dict())
        text = corporate_gateway.complete(prompt, model="approved-model-v1")
        return ProfileResult(
            markdown=text,
            usage=usage,
            scoring=build_scoring_result(usage),
            source="gateway",
        )
```

Retain `build_scoring_result()` unless the enterprise segmentation service becomes the system of record for archetype labels—in that case, map API response fields into `ScoringResult` for UI and analytics consistency.

---

## 5. Replacing rule-based logic

| Prototype component | Production replacement |
|--------------------|-------------------------|
| `render_profile_report` | Segmentation API response formatter |
| `render_offer_report` | PCM recommendation engine |
| `data/tariffs_private.md` | Catalogue sync job or API cache |
| `data/consumer_archetypes.md` | Segment definition service export |

Inject providers at `ProfilerEngine` construction; avoid forking the Gradio layer.

---

## 6. UI and headless consumption

### 6.1 Current Gradio session model

The UI stores `ProfileResult` in `gr.State` via `to_state_dict()`. The offer step deserialises with `ProfileResult.from_state_dict()` and rejects placeholders.

Integrators embedding Gradio behind SSO should treat session state as browser-local; do not rely on it for server-side audit.

### 6.2 Headless API (recommended for production)

Expose `ProfilerEngine` through an internal REST layer:

```python
@app.post("/v1/profile")
def api_profile(body: UsagePayload) -> ProfileResponse:
    usage = CustomerUsage.from_mapping(body.model_dump(), clamp=True)
    result = get_engine().profile(usage)
    return ProfileResponse(
        markdown=result.markdown,
        primary=result.scoring.primary.name if result.scoring else None,
        confidence=result.scoring.confidence if result.scoring else None,
        source=result.source,
    )
```

Apply authentication, rate limiting, and request logging at this boundary.

### 6.3 Agent desktop embedding

- **Iframe:** Host Gradio behind reverse proxy + SSO.  
- **API + native UI:** Preferred for long-term maintainability and accessibility requirements.

---

## 7. Batch and campaign processing

```python
from telekom_profiler.services import ProfilerEngine
from telekom_profiler.domain import CustomerUsage

engine = ProfilerEngine()
for row in usage_feed:
    usage = CustomerUsage.from_mapping(row, clamp=True)
    profile = engine.profile(usage)
    offer = engine.recommend(profile, usage)
    write_campaign_output(profile, offer)
```

Run with `OLLAMA_ENABLED=false` for deterministic regression baselines, or queue LLM calls with rate limits and dead-letter handling.

---

## 8. Prompt and catalogue governance

| Asset | Suggested owner | Cadence |
|-------|-----------------|---------|
| `consumer_archetypes.md` | Marketing / segmentation | Per archetype definition change |
| `tariffs_private.md` | Product management | Per tariff release |
| `run_profile.md`, `run_offer.md` | AI governance | Per approved model version |

Version prompts with application releases; maintain model cards and approval records per corporate AI policy.

---

## 9. Integration testing

| Test type | Approach |
|-----------|----------|
| Unit | Mock external APIs; assert `ProfileResult` and `ScoringResult` |
| Contract | Shared JSON schema for `CustomerUsage` with upstream teams |
| CI | `OLLAMA_ENABLED=false`; full unittest + sanity script |
| E2E (optional) | Staged gateway with test credentials |

---

## 10. Related documents

- [Architecture](architecture.md) — extension points  
- [Deployment](deployment.md) — hosting and security  
- [ADR 001](adr/001-scoring-in-code.md) — scoring policy  
