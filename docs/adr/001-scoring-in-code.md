# ADR 001: Deterministic archetype scoring in code

## Status

Accepted

## Context

The Private Customer Profiler assigns each subscriber to one of five B2C usage archetypes (Streamer, Chatterbox, Essential, Roamer, Messenger). We can compute proximity scores in Python (L1 distance on normalized usage) or let an LLM infer the segment from free text.

Campaign and pricing teams need **auditable, repeatable** segment labels for analytics, A/B tests, and CRM workflows. LLM narratives are useful for agents but can drift from the numeric snapshot.

## Decision

1. **Always compute** `ScoringResult` in code via `build_scoring_result()` before any profile is returned.
2. **Inject** `required_primary` and `required_confidence` into the LLM profile prompt so the narrative aligns with code scoring.
3. **Display** scoring metadata in the UI (primary, confidence, overlays) independent of profile markdown.
4. **Use** `scoring.primary_name` in rule-based offer selection when available.

## Consequences

- LLM creativity is constrained for section 1 (primary archetype); agents still get rich narrative in other sections.
- Scoring can be logged and compared to model output for governance.
- Future segmentation APIs can replace `build_scoring_result()` while keeping the same `ScoringResult` contract.

## Alternatives considered

- **LLM-only segmentation** — rejected for lack of audit trail.
- **Post-process LLM output** to extract archetype — fragile parsing; rejected.
- **Hide scoring from UI** — rejected; agents benefit from seeing ground truth.
