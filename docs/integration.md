# Integration guide

How to connect the profiler to Telekom Mobile systems of record and approved AI services.

## Integration roadmap

| Phase | Capability | Integration point |
|-------|------------|-------------------|
| 1 (today) | Manual sliders + prototype logic | `ui.demo` |
| 2 | Typed state, no markdown coupling | `ProfileResult` + `gr.State` |
| 3 | Segmentation service | Custom `ProfileProvider` |
| 4 | Live PCM / BSS catalogue | Custom `OfferProvider` + tariff API |
| 5 | CRM write-back | New service after offer approval |

## Recommended API contract

### Input: usage vector

Use `CustomerUsage` (or JSON with the six keys from [Domain model](domain-model.md)).

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

Populate from billing (last 3 months average), CDR aggregation, or CRM attributes.

### Output: profile

Prefer structured `ProfileResult`:

```python
from telekom_profiler.services import ProfilerEngine, profile_customer_structured

result = profile_customer_structured(usage_dict)
segment = result.scoring.primary_name if result.scoring else None
markdown_for_agent = result.markdown
```

### Output: offer

Markdown string suitable for agent desktop or PDF generation. Parse tables in downstream systems if needed, or extend `OfferProvider` to return JSON.

## Replacing the LLM

Implement `ProfileProvider` / `OfferProvider` calling your approved gateway:

```python
class GatewayProfileProvider:
    def profile(self, usage: CustomerUsage) -> ProfileResult:
        prompt = build_profile_prompt(usage.as_dict())
        text = your_gateway.complete(prompt, model="approved-model")
        return ProfileResult(
            markdown=text,
            usage=usage,
            scoring=build_scoring_result(usage),
            source="gateway",
        )
```

Keep `build_scoring_result()` for consistent archetype metadata in analytics.

## Replacing rule-based logic

| Function | Replace with |
|----------|--------------|
| `render_profile_report` | Segmentation API response formatter |
| `render_offer_report` | PCM recommendation engine |
| `data/tariffs_private.md` | Product catalogue sync |

## UI state: stop passing markdown

Current Gradio flow passes profile **markdown** into the offer step. For production:

```python
profile_state = gr.State(value=None)

def run_profile(*values):
    result = profile_customer_structured(_slider_data(*values))
    return result.markdown, MSG_AFTER_PROFILE, result

run_btn.click(..., outputs=[profile_out, offer_hint, profile_state])
offer_btn.click(generate_offer, inputs=[profile_state, *all_inputs], ...)
```

Implement `generate_offer(profile: ProfileResult | None, ...)` to use typed state.

## CRM / agent desktop

- Embed Gradio in iframe behind SSO, or
- Expose `ProfilerEngine` via FastAPI:

```python
@app.post("/v1/profile")
def api_profile(body: UsagePayload) -> ProfileResponse:
    result = get_engine().profile(body.to_usage())
    return ProfileResponse(markdown=result.markdown, primary=result.scoring.primary_name)
```

## Batch / campaign use

```python
engine = ProfilerEngine()
for row in usage_feed:
    usage = CustomerUsage.from_mapping(row)
    profile = engine.profile(usage)
    offer = engine.recommend(profile, usage)
    write_to_campaign_file(profile, offer)
```

## Prompt and catalogue maintenance

| Asset | Owner | Update cadence |
|-------|-------|----------------|
| `consumer_archetypes.md` | Marketing / segmentation | Per archetype refresh |
| `tariffs_private.md` | Product management | Per tariff change |
| `run_profile.md` / `run_offer.md` | Data science / AI governance | Per model policy |

Version prompts with git tags; align with model cards for compliance.

## Testing integrations

1. Mock external APIs in unit tests.
2. Use `OLLAMA_ENABLED=false` for deterministic CI.
3. Contract tests on `CustomerUsage` JSON schema shared with upstream teams.
