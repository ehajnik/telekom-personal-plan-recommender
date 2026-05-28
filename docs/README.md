# Documentation

Technical documentation for the **Private Customer Profiler** — a Telekom Mobile B2C application for usage-driven customer profiling and tariff recommendation.

## Current state at a glance

The documentation reflects a **working internal prototype** with deterministic business logic and optional LLM enrichment.

- Profile/offer flow is feature-complete for workshops and internal validation.
- Scoring is deterministic by design; LLM output is presentation, not ground truth.
- ML artifacts are frozen for runtime consistency; retraining is a controlled maintenance task.
- Production controls (SSO, audit logging, secret management, full compliance hardening) are documented as target-state work, not delivered runtime capabilities.

Why this framing: teams can safely iterate on business behavior and integration boundaries without conflating demo-readiness with production-readiness.

## Document catalogue

| Document | Primary audience | Purpose |
|----------|------------------|---------|
| [Architecture](architecture.md) | Solution architects, tech leads | System structure, boundaries, extension points |
| [Domain model](domain-model.md) | Product, data science, engineering | Usage signals, archetypes, scoring semantics |
| [Configuration](configuration.md) | Developers, platform engineers | Environment variables, sliders, presets |
| [Development](development.md) | Software engineers | Local setup, conventions, change workflow |
| [Deployment](deployment.md) | Platform / SRE | Hardening, hosting, security, observability |
| [Integration](integration.md) | Integration architects | CRM, BSS, LLM gateway, batch processing |
| [API reference](api-reference.md) | Developers | Public Python surface |
| [Ollama runbook](runbook-ollama.md) | Operations, support | LLM inference troubleshooting |
| [ADR 001: Scoring in code](adr/001-scoring-in-code.md) | Architects, governance | Design decision on deterministic scoring |

## Recommended reading paths

### New engineer (first week)

1. [Architecture](architecture.md) — understand layers and provider model  
2. [Development](development.md) — environment, tests, coding standards  
3. [Domain model](domain-model.md) — business vocabulary and data contracts  
4. [API reference](api-reference.md) — programmatic entry points  

### Integration / backend team

1. [Integration](integration.md) — phased replacement of stubs  
2. [Domain model](domain-model.md) — `CustomerUsage` and `ProfileResult` contracts  
3. [Configuration](configuration.md) — environment and feature flags  
4. [ADR 001](adr/001-scoring-in-code.md) — scoring vs. LLM narrative  

### Platform / operations

1. [Deployment](deployment.md) — target topology and security checklist  
2. [Configuration](configuration.md) — runtime settings  
3. [Ollama runbook](runbook-ollama.md) — LLM service operations  

### Product / campaign stakeholders

1. [Domain model](domain-model.md) — archetypes, overlays, feature definitions  
2. Root [README](../README.md) — scope, workflow, and limitations  

## Repository map (documentation vs. code)

| Path | Role |
|------|------|
| `telekom_profiler/` | Application source (installable package) |
| `docs/` | Architecture and operational documentation |
| `tests/` | Unit tests (run in CI) |
| `scripts/sanity_check.py` | Smoke validation without Ollama |
| `.github/workflows/ci.yml` | Automated quality gate on `main` |

## Maintaining this documentation

Update documentation in the **same change** as code when you alter:

- Public APIs (`telekom_profiler.services`, domain models)
- Environment variables (`.env.example`, `config/ollama_settings.py`)
- Archetype definitions, thresholds, or prompt templates
- Integration contracts described in [Integration](integration.md)

For architectural decisions, add an ADR under `docs/adr/` and link it from this index.
