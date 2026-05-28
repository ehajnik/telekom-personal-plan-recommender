# Private Customer Profiler

**Telekom Mobile — B2C usage-driven profiling and plan recommendation**

Internal application supporting sales and marketing workflows: capture monthly usage and behavioural signals, derive a structured customer profile, and produce a tariff recommendation aligned with Telekom Mobile private tariffs.

The solution is delivered as an installable Python package (`telekom_profiler`) with a Gradio presentation layer, Deutsche Telekom branding, and **pluggable backends** for profiling and offer generation. This structure allows teams to replace prototype logic with production services (segmentation APIs, PCM/BSS catalogues, approved LLM gateways) without redesigning the user interface.

| | |
|---|---|
| **Status** | Development prototype — not production-certified |
| **Documentation** | [docs/](docs/README.md) |
| **Python** | 3.10+ |
| **CI** | Unit tests, sanity checks, ruff, mypy (see `.github/workflows/ci.yml`) |
| **Version** | Semver via Commitizen — see [Versioning](docs/development.md#12-versioning-and-releases) |

---

## Current project state

This repository is in a **stabilized prototype** phase: the core profiling and recommendation flow is functional and test-covered, while enterprise integration concerns are intentionally deferred.

| Area | Current state | Why it is this way |
|------|---------------|--------------------|
| Core domain scoring | Stable and deterministic | Sales workflows need explainable, repeatable outputs; deterministic scoring prevents narrative drift from changing profile assignments. |
| UI workflow | Stable for workshops and internal demos | Product validation and stakeholder feedback are faster with a runnable end-to-end UI than with backend-only prototypes. |
| ML segmentation runtime | Frozen-centroid inference from committed artifacts | Pipeline is staged: generate synthetic data, define/curate archetypes, then freeze artifacts for runtime inference. |
| LLM narrative layer | Optional enhancement with rule-based fallback | Narrative quality improves user experience, but business decisions must not depend on external model availability or latency. |
| External integration (CRM/BSS/SSO/audit) | Not production-complete | Integration and governance requirements are organization-specific and are separated from the prototype to reduce coupling early. |

**Bottom line:** this codebase is optimized for correctness and explainability of recommendation logic first, and for enterprise hardening second.

---

## Business capability

| Capability | Description |
|------------|-------------|
| Usage capture | Six standardised signals (four usage levels, two trends) via UI or API |
| Customer profiling | Markdown profile with archetype, overlays, narrative, and risks |
| Offer recommendation | Tariff and add-on suggestion against prototype catalogue |
| Demo personas | Profile templates from ML training or legacy archetype presets |
| ML segmentation | Staged K-Means workflow on 12-month synthetic usage (`n_profiles` from config, currently 5), Hungarian label matching, and frozen-centroid runtime inference |
| Inference modes | LiteLLM (Ollama endpoint by default) with runtime model dropdown and rule-based / ML fallback |

### Out of scope (current release)

CRM or billing integration, real-time CDR feeds, production SSO, central audit logging, live product catalogue APIs, and formal data-residency controls. See [Integration roadmap](docs/integration.md#integration-roadmap).

---

## Standard user workflow

1. Pick a **profile template** or adjust **usage features** and **trends**.  
2. Click **Profile** — primary profile, distance table, overlay badges, metric-backed narrative.  
3. Click **Generate offer** — plan recommendation with catalog SKUs (requires completed profile).

Default local URL: `http://127.0.0.1:7860` (port assigned by Gradio; confirm in terminal output).

---

## Quick start

```bash
git clone <repository-url>
cd telekom-personal-plan-recommender

# One-shot: .venv + pip install -e ".[dev,ml]" + .env from example
./scripts/setup.sh
# Or: make setup

source .venv/bin/activate

# ML PoC pipeline:
#   1) generate synthetic data
#   2) train/update archetypes + centroids
#   3) freeze runtime artifacts
# If the synthetic dataset changes, you MUST refresh:
#   1) model.fixed_centroids in app_config.yaml
#   2) curated profile definitions in telekom_profiler/ml/profile_characteristics.py
#   3) regenerate artifacts/profile_characteristics.json + frozen_centroids.json via one training run
# WARNING: retraining without updating the hardcoded profile layer creates config/profile drift.
# Keep runtime inference frozen between dataset refreshes (no dynamic runtime retraining).
python scripts/generate_synthetic_data.py --subscribers 1000
# Optional: MOSTLY AI-backed generator (requires requirements-mostlyai.txt)
# python scripts/generate_synthetic_data_mostlyai.py --subscribers 1000
python scripts/subscriber_profiling.py --input data/raw/private_mobile_usage_1000_subscribers_12_months.csv
# writes frozen runtime artifacts (frozen_centroids.json, label_map.json, profile_characteristics.json)
# if synthetic data changes, clustering/archetype mapping can shift and must be re-curated

# Optional LLM (CPU-friendly defaults in .env.example):
# ollama serve && ollama pull qwen2.5:7b

python app.py
```

Set `PROFILER_MODE=auto` (default) to use ML when `artifacts/` exists, else legacy rule-based archetypes.

| Command | Purpose |
|---------|---------|
| `python app.py` | Launch UI |
| `python -m telekom_profiler` | Same entry via package module |
| `telekom-profiler` | Console script after `pip install -e .` |

Optional MOSTLY AI integration:

```bash
pip install -r requirements-mostlyai.txt
# Or: pip install -e ".[mostlyai]"

# Uses the latest panel under data/raw/ as the training seed by default.
python scripts/generate_synthetic_data_mostlyai.py --subscribers 1000
python scripts/subscriber_profiling.py \
  --input data/raw/private_mobile_usage_mostlyai_1000_subscribers_12_months.csv
```

The MOSTLY AI path keeps the existing deterministic generator as a fallback and writes its workspace under `artifacts/mostlyai/`.

**Quality gate (before merge):**

```bash
OLLAMA_ENABLED=false PROFILER_MODE=rules python -m unittest discover -s tests -v
OLLAMA_ENABLED=false PROFILER_MODE=rules python scripts/sanity_check.py
ruff check telekom_profiler tests scripts
mypy telekom_profiler
```

`PROFILER_MODE=rules` pins the legacy archetype scoring so unit-test assertions about archetype names (e.g. `Streamer`) are independent of any locally-trained `artifacts/`.

---

## Architecture summary

The application follows a **layered, provider-based** design:

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Presentation | `telekom_profiler.ui` | Gradio UI, Telekom theme, session state |
| Application | `telekom_profiler.services` | `ProfilerEngine`, provider orchestration |
| Domain | `telekom_profiler.domain` | Models, archetype scoring, rule engines |
| Integration | `prompts`, `llm`, `data` | Prompt assembly, Ollama client, reference data |
| ML pipeline | `telekom_profiler.ml`, `scripts/` | Synthetic data, feature engineering, K-Means training |
| Configuration | `telekom_profiler.config` | Sliders, thresholds, environment, profiler mode |

**Design principles:**

- **Deterministic scoring** runs in code for every profile; LLM output is narrative enrichment (see [ADR 001](docs/adr/001-scoring-in-code.md)).  
- **Provider protocols** (`ProfileProvider`, `OfferProvider`) enable backend substitution.  
- **Typed contracts** (`CustomerUsage`, `ProfileResult`) support CRM and API integration.

Full detail: [docs/architecture.md](docs/architecture.md).

---

## Configuration overview

| Area | Location |
|------|----------|
| LiteLLM/Ollama runtime and logging | `.env` (see `.env.example`) |
| Core model/runtime/UI knobs | `app_config.yaml` (repo root) |
| Sliders and presets (resolved from root config) | `telekom_profiler/config/sliders.py` |
| Business thresholds | `telekom_profiler/config/thresholds.py` |
| Prompt templates | `telekom_profiler/prompts/templates/` |
| Reference catalogues | `telekom_profiler/data/` |

Reference: [docs/configuration.md](docs/configuration.md). LLM operations: [docs/runbook-ollama.md](docs/runbook-ollama.md).

The model list for the UI dropdown is centrally managed in `app_config.yaml` under `llm.models` with `llm.default_model`.
Cloud providers (`openai/*`, `anthropic/*`, `gemini/*`) require valid API keys and usually paid billing accounts.

---

## Repository structure

```
telekom-personal-plan-recommender/
├── app.py                    # Application entry point
├── pyproject.toml            # Package metadata, dev tools, CI dependencies
├── requirements.txt          # Runtime dependencies
├── docs/                     # Technical documentation
├── scripts/sanity_check.py   # Smoke tests (no Ollama required)
├── tests/                    # Unit test suite
└── telekom_profiler/         # Application package
    ├── config/               # Sliders, thresholds, Ollama settings
    ├── domain/               # Models, scoring, rule-based engines
    ├── services/             # Engine, providers, public API
    ├── prompts/              # Template builder
    ├── llm/                  # Ollama client
    ├── data/                 # Archetype and tariff reference (markdown)
    ├── ui/                   # Gradio application and theme
    └── assets/               # Brand assets
```

---

## Feature model (summary)

**Usage features** (monthly levels — input to archetype distance): `data_gb`, `voice_min`, `sms_count`, `roaming_days`.

**Trends** (trajectory indicators, −50…+50): `data_trend`, `voice_trend`. Trends drive overlay flags and narrative context; they are not clustering inputs unless a downstream model defines otherwise.

Complete specification: [docs/domain-model.md](docs/domain-model.md).

---

## Integration and extension

Programmatic usage:

```python
from telekom_profiler.domain import CustomerUsage
from telekom_profiler.services import profile_customer_structured, get_engine

usage = CustomerUsage.from_mapping({...}, clamp=True)
result = profile_customer_structured(usage.as_dict())
offer_md = get_engine().recommend(result, usage)
```

Phased production integration (CRM, segmentation API, PCM): [docs/integration.md](docs/integration.md).

---

## Operations

| Topic | Document |
|-------|----------|
| Local troubleshooting | [docs/development.md](docs/development.md) |
| LLM / Ollama | [docs/runbook-ollama.md](docs/runbook-ollama.md) |
| Deployment target state | [docs/deployment.md](docs/deployment.md) |
| API surface | [docs/api-reference.md](docs/api-reference.md) |

---

## Compliance and disclaimer

This repository is an **internal technical demonstrator**. Brand assets and tariff data are for development and demonstration. Production deployment requires security assessment, GDPR review, AI governance approval, and adherence to Deutsche Telekom brand and software standards.
