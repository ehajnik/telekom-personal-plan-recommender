# ADR 001: Deterministic archetype scoring in application code

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025 (prototype baseline) |
| **Deciders** | Application architecture (Private Customer Profiler) |
| **Supersedes** | — |

---

## Context

The Private Customer Profiler assigns each subscriber to one primary usage profile from a fixed five-profile taxonomy. In ML mode, labels come from the frozen centroid set (`Light / occasional user`, `Streaming & data-heavy`, `Voice-centric`, `Roaming / travel-heavy`, `Value optimization candidate`). In rules mode (`PROFILER_MODE=rules`), legacy archetype names (`Streamer`, `Chatterbox`, `Essential`, `Roamer`, `Messenger`) remain available for deterministic fallback and test stability.

Across both modes, proximity scoring can be computed deterministically in Python, while LLM output remains narrative-only.

Campaign, pricing, and CRM teams require **auditable, repeatable** segment labels for analytics, targeting, and approval workflows. LLM output is valuable for agent-facing explanation but is not a suitable system of record for segment identity.

---

## Decision

1. **Always compute** `ScoringResult` via `build_scoring_result()` before returning any profile from built-in providers.  
2. **Inject** `required_primary` and `required_confidence` into the LLM profile prompt so narrative section 1 aligns with code scoring.  
3. **Display** scoring metadata in the UI (primary archetype, confidence, overlays) independently of profile markdown.  
4. **Use** `scoring.primary.name` in rule-based offer selection when available.  
5. **Expose** `ScoringResult` on `ProfileResult` for API and batch integrators.

---

## Consequences

### Positive

- Segment labels are reproducible from the same usage input.  
- Analytics and A/B tests can key on `ScoringResult` without parsing markdown.  
- Governance can compare LLM narrative to deterministic primary over time.  
- Future enterprise segmentation APIs can populate the same `ScoringResult` shape.

### Negative / trade-offs

- LLM creativity is constrained for primary archetype wording.  
- Additional UI surface (scoring summary panel) must be maintained.  
- Teams must not treat free-text profile output as authoritative segment ID.

---

## Alternatives considered

| Alternative | Outcome |
|-------------|---------|
| LLM-only segmentation | Rejected — no audit trail, non-deterministic |
| Post-process LLM markdown to extract archetype | Rejected — fragile, high maintenance |
| Hide scoring from UI | Rejected — agents benefit from deterministic ground truth |

---

## Compliance and follow-up

- Document segment definitions in [Domain model](../domain-model.md).  
- When connecting to a corporate segmentation API, either map API segment IDs into `ScoringResult` or replace `build_scoring_result()` behind the same contract.  
- Review this ADR when AI governance policy changes for customer-facing inference.

---

## References

- [Architecture](../architecture.md) — scoring pipeline  
- [Integration](../integration.md) — CRM and analytics consumption  
