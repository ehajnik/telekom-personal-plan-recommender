# Architecture

## 1. Purpose and scope

The Private Customer Profiler is an internal **presentation-layer application** for Telekom Mobile B2C use cases. It accepts a standardised usage snapshot, produces a customer profile, and recommends a tariff configuration.

The codebase is intentionally structured for **incremental industrialisation**: prototype rule engines and local Ollama inference can be replaced by enterprise services (segmentation platforms, PCM/BSS catalogues, approved model gateways) through well-defined extension points, without rewriting the Gradio front end.

This document describes the logical architecture, request flows, and scalability mechanisms. Deployment and security considerations are covered in [Deployment](deployment.md).

---

## 2. Architectural principles

| Principle | Implementation |
|-----------|----------------|
| Separation of concerns | Distinct packages for UI, orchestration, domain logic, and integration |
| Pluggable backends | `ProfileProvider` and `OfferProvider` protocols |
| Auditable segmentation | Deterministic `ScoringResult` computed in code for every profile |
| Stable contracts | `CustomerUsage` (input) and `ProfileResult` (profile output) |
| Configuration externalisation | Root `app_config.yaml` plus env bindings in `config/` |
| Fail-safe inference | Optional fallback from LiteLLM to rule-based / ML providers |
| Single catalogue source | `domain/catalog.py` for rules; markdown for LLM; consistency enforced by tests |

Design rationale for deterministic scoring: [ADR 001](adr/001-scoring-in-code.md).

---

## 2.1 Why the architecture looks like this

The current architecture is intentionally biased toward **auditability and replaceability** over short-term model sophistication:

- Deterministic scoring stays in code so profile labels and confidence remain explainable in sales and governance discussions.
- LLM usage is isolated behind providers so model/vendor changes do not force UI or domain rewrites.
- Fallback providers are first-class because local model serving on laptops is variable and must not block the business flow.
- Config is centralized (`app_config.yaml` + env) to reduce "hidden behavior" and make workshop behavior reproducible.
- Runtime ML is frozen to avoid accidental drift across environments and to keep CI expectations stable.

This is a deliberate tradeoff: slightly less automation in exchange for operational predictability and safer industrialization.

---

## 3. Layered structure

```mermaid
flowchart TB
  subgraph presentation [Presentation layer]
    UI[ui.demo — Gradio]
    Theme[ui.theme]
  end

  subgraph application [Application layer]
    API[services.analysis — public API]
    Engine[services.engine.ProfilerEngine]
    Providers[services.providers / fallback]
  end

  subgraph domain [Domain layer]
    Models[domain.models]
    Scoring[domain.scoring / archetypes]
    Rules[profiling / offers — rule engines]
  end

  subgraph integration [Integration layer]
    Prompts[prompts.builder + templates]
    LLM[llm.client]
    Data[data — reference markdown]
  end

  UI --> API
  UI --> Theme
  API --> Engine
  Engine --> Providers
  Providers --> Rules
  Providers --> LLM
  Providers --> Prompts
  Prompts --> Scoring
  Rules --> Scoring
  Rules --> Models
```

### Layer responsibilities

| Layer | Package | Owns |
|-------|---------|------|
| Presentation | `telekom_profiler.ui` | Layout, events, branding, `gr.State` session data |
| Application | `telekom_profiler.services` | Provider selection, orchestration, public API |
| Domain | `telekom_profiler.domain` | Business rules, archetype mathematics, typed models |
| Integration | `prompts`, `llm`, `data` | Prompt construction, HTTP client, static reference data |
| Configuration | `telekom_profiler.config` | Root YAML loader, slider resolution, thresholds, environment bindings |

**Dependency rule:** Presentation and Application depend on Domain; Domain does not depend on UI or Gradio. Integration adapters are invoked from Application providers only.

---

## 4. Core components

### 4.1 ProfilerEngine

`ProfilerEngine` (`services/engine.py`) is the central orchestrator. It accepts `CustomerUsage` (or compatible mappings), delegates to injected providers, and returns `ProfileResult` or offer markdown.

- Default providers are selected via `default_profile_provider()` / `default_offer_provider()` based on environment flags.
- `get_engine()` exposes a process-wide singleton for the UI; `reset_engine()` rebuilds providers after configuration changes (used at startup and in tests).
- Custom deployments should prefer explicit `ProfilerEngine(...)` construction for testability and multi-tenant scenarios.

### 4.2 Provider model

| Protocol | Method | Output |
|----------|--------|--------|
| `ProfileProvider` | `profile(usage)` | `ProfileResult` |
| `OfferProvider` | `recommend(profile, usage)` | Offer markdown (`str`) |

Built-in implementations:

| Implementation | `source` tag | Use case |
|----------------|--------------|----------|
| `RuleBasedProfileProvider` | `rule_based` | Deterministic legacy archetypes (rules mode), CI |
| `MlProfileProvider` | `ml_kmeans` | Frozen K-Means profile (ML mode) |
| `LiteLLMProfileProvider` (alias `OllamaProfileProvider`) | `litellm/<provider>` | LLM narrative |
| `FallbackProfileProvider` | `rule_based_fallback` | LLM failure → ML or rules provider |
| `RuleBasedOfferProvider` | `rule_based` | Allowance-based sizing against `domain/catalog.py` |
| `LiteLLMOfferProvider` (alias `OllamaOfferProvider`) | `litellm/<provider>` | LLM offer narrative grounded with the rule sizing |
| `FallbackOfferProvider` | (via rules) | LLM failure handling |

### 4.3 Scoring pipeline

For every profile request—regardless of provider—`build_scoring_result()` computes:

- Ranked profile distances (ML: Euclidean on standardised log usage vs frozen centroids; rules: L1 on slider-normalised usage)
- Primary and secondary archetype
- Overlay flags (trend and usage thresholds)
- Confidence label (`High` / `Medium` / `Low`)

This result is attached to `ProfileResult.scoring` and displayed in the UI independently of LLM-generated markdown.

---

## 5. Request flows

### 5.1 Profile generation

```mermaid
sequenceDiagram
  participant UI as Gradio UI
  participant API as profile_customer_structured
  participant Engine as ProfilerEngine
  participant Prov as ProfileProvider
  participant Score as build_scoring_result

  UI->>API: slider values
  API->>Engine: CustomerUsage
  Engine->>Prov: profile(usage)
  Prov->>Score: scoring (always)
  Prov-->>Engine: ProfileResult
  Engine-->>API: ProfileResult
  API-->>UI: markdown + state dict + scoring panel
```

1. UI collects six slider values; values are clamped to configured bounds.  
2. `profile_customer_structured()` invokes `ProfilerEngine.profile()`.  
3. Active provider generates profile markdown (rules, ML or LiteLLM).  
4. Scoring metadata is attached and persisted in `gr.State` for the offer step.

### 5.2 Offer generation

1. UI reads `ProfileResult` from session state (placeholder profiles are rejected; if the sliders changed since profiling the user is asked to re-run the profile).  
2. `ProfilerEngine.recommend()` re-scores the usage and invokes the active `OfferProvider`.  
3. Rule-based offers size the tariff by allowance; `scoring.primary` sets channel and minimum tier.  
4. Offer markdown is rendered in the results panel.

---

## 6. Extension points (scalability)

| Enterprise need | Extension mechanism | Typical owner |
|-----------------|---------------------|---------------|
| Corporate LLM gateway | New `ProfileProvider` / `OfferProvider` | AI platform team |
| Segmentation API | Replace or wrap `RuleBasedProfileProvider` | Data science / CRM |
| Live PCM catalogue | Custom `OfferProvider` + API client | Product / BSS |
| CRM-fed usage | Upstream builds `CustomerUsage` JSON | Integration team |
| Presets from CMDB | Sync `app_config.yaml` with external config source | Configuration management |
| Headless API | FastAPI layer over `ProfilerEngine` | Application team |
| Multi-brand | Per-tenant `ProfilerEngine(custom_providers)` | Platform team |

Detailed integration patterns: [Integration](integration.md).

---

## 7. Configuration and reference data

| Concern | Location |
|---------|----------|
| Core model/runtime/UI knobs | `app_config.yaml` |
| Slider bounds and UI copy | `config/sliders.py` (resolved from root YAML) |
| Overlay and offer thresholds | `config/thresholds.py` |
| Ollama and logging | `config/ollama_settings.py`, `.env` |
| Profile narratives | `data/consumer_archetypes.md`, `ml/profile_characteristics.py` |
| Tariff reference | `domain/catalog.py` (rules), `data/plans_and_options.md` (LLM) |
| Prompt templates | `prompts/templates/*.md` |

Path resolution is centralised in `telekom_profiler.paths` to support packaging and testing.

---

## 8. Technology dependencies

| Dependency | Role in architecture |
|------------|---------------------|
| `gradio` | Presentation framework |
| `litellm` | LLM client (local Ollama by default; OpenAI / Anthropic / Gemini optional) |
| `python-dotenv`, `pyyaml` | Environment and `app_config.yaml` loading |
| `scikit-learn`, `pandas`, `numpy`, `scipy` (extra `ml`) | Training, evaluation and ML inference |

No database, message broker, or external service is required for baseline operation.

---

## 9. Non-goals (current release)

The following are explicitly **not** implemented; plan via [Deployment](deployment.md) and [Integration](integration.md):

- Authentication and authorisation (SSO/RBAC)
- Horizontal autoscaling and health endpoints
- Centralised secret management
- PII encryption, retention policies, and audit trails
- Prompt governance pipelines and LLM output evaluation (segmentation is evaluated by `scripts/evaluate_model.py`)
- Per-session LLM model selection (the UI model dropdown changes a process-wide setting shared by all users)

---

## 10. Related documents

- [Domain model](domain-model.md) — data definitions and archetype semantics  
- [Development](development.md) — engineering workflow  
- [API reference](api-reference.md) — public Python surface  
- [Configuration](configuration.md) — runtime settings  
