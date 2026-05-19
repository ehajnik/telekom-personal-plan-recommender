# Development guide

Engineering handbook for contributing to the Private Customer Profiler. For system design, see [Architecture](architecture.md). For runtime settings, see [Configuration](configuration.md).

---

## 1. Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| Python | 3.10 or later (matches `pyproject.toml`) |
| Git | Access to the corporate repository |
| Ollama | Optional; required only when `OLLAMA_ENABLED=true` |

On Fedora, install the venv module if needed: `sudo dnf install python3-venv`.

---

## 2. Environment setup

```bash
git clone <repository-url>
cd telekom-personal-plan-recommender

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev,ml]"

cp .env.example .env
# Optional LLM path:
ollama serve
ollama pull llama3.2
```

The editable install (`pip install -e .`) registers the `telekom-profiler` console script and ensures imports resolve as `telekom_profiler`.

---

## 3. Running the application

| Command | Description |
|---------|-------------|
| `python app.py` | Primary entry point |
| `python -m telekom_profiler` | Package module entry |
| `telekom-profiler` | Console script (after editable install) |

The process prints the Gradio URL (typically `http://127.0.0.1:7860`). Port assignment is dynamic unless configured in `ui/demo.py`.

---

## 4. ML profiling pipeline (PoC)

Generate synthetic billing history and train K-Means profiles (writes to `artifacts/`, gitignored):

```bash
python scripts/generate_synthetic_data.py --subscribers 1000 --seed 42
python scripts/subscriber_profiling.py --min-silhouette 0.5
```

| Output | Purpose |
|--------|---------|
| `data/raw/private_mobile_usage_*_12_months.csv` | Monthly panel input |
| `artifacts/kmeans.pkl`, `scaler.pkl` | Trained model |
| `artifacts/subscriber_cluster_map.csv` | Subscriber dropdown + distances |
| `artifacts/profile_characteristics.json` | Profile labels and slider presets |

**Design rule:** trend columns are excluded from `CLUSTER_FEATURES`; they feed overlays only.

Set `PROFILER_MODE=rules` to force legacy L1 archetypes (used in unit tests). Default `auto` selects ML when artifacts exist.

---

## 5. Quality assurance

Run the full gate locally before opening a pull request (mirrors CI):

```bash
export OLLAMA_ENABLED=false

python -m unittest discover -s tests -v
python scripts/sanity_check.py
ruff check telekom_profiler tests scripts
mypy telekom_profiler
```

| Check | Purpose |
|-------|---------|
| Unit tests | Domain logic, providers, prompts, models |
| `scripts/sanity_check.py` | Import graph, template placeholders, UI construction |
| Ruff | Style and import order |
| Mypy | Static typing on `telekom_profiler` |

CI configuration: `.github/workflows/ci.yml`.

---

## 6. Engineering conventions

| Topic | Standard |
|-------|----------|
| Style | PEP 8; line length 100 (Ruff) |
| Typing | Type hints on public APIs; `from __future__ import annotations` in new modules |
| Imports | Absolute imports from `telekom_profiler` |
| Paths | `telekom_profiler.paths` — no hard-coded relative paths from CWD |
| Configuration | Environment in `config/ollama_settings.py`; UI bounds in `config/sliders.py`; business rules in `config/thresholds.py` |
| UI styling | Semantic `elem_classes` in `ui/theme/app.css` |
| Logging | `logging_config.configure_logging()` at startup; module loggers |

### Change discipline

- Update [documentation](README.md) when altering public APIs, environment variables, archetypes, or integration contracts.
- Record significant design decisions as ADRs under `docs/adr/`.
- Prefer extending providers over branching logic inside the UI layer.

---

## 7. Extending providers

### 7.1 Profile provider

Implement `ProfileProvider` and inject into `ProfilerEngine`:

```python
from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.domain.scoring import build_scoring_result
from telekom_profiler.services.protocols import ProfileProvider

class SegmentationApiProfileProvider:
    def profile(self, usage: CustomerUsage) -> ProfileResult:
        segment_id = call_segmentation_api(usage)
        markdown = format_segment_markdown(segment_id)
        return ProfileResult(
            markdown=markdown,
            usage=usage,
            scoring=build_scoring_result(usage),
            source="segmentation_api",
        )
```

```python
engine = ProfilerEngine(profile_provider=SegmentationApiProfileProvider())
result = engine.profile(usage)
```

Add unit tests with mocked HTTP; do not require Ollama in CI.

### 7.2 Offer provider

Implement `OfferProvider.recommend(profile: ProfileResult, usage: CustomerUsage) -> str` using the same injection pattern.

Further integration patterns: [Integration guide](integration.md).

---

## 8. Modifying prompts and reference data

| Asset | Location | Validation |
|-------|----------|------------|
| Profile template | `prompts/templates/run_profile.md` | `scripts/sanity_check.py` |
| Offer template | `prompts/templates/run_offer.md` | same |
| Placeholder binding | `prompts/builder.py` | same |
| Archetype narratives | `data/consumer_archetypes.md` | Manual review |
| Tariff catalogue | `data/tariffs_private.md` | Manual review |

Templates use `{placeholder}` syntax. After edits, run the sanity script to detect unfilled tokens.

---

## 9. Modifying archetypes and presets

1. Update `ARCHETYPE_CENTROIDS` in `domain/archetypes.py`.
2. Align `PROFILES` presets in `config/sliders.py` for demo consistency.
3. Update `data/consumer_archetypes.md` narrative content.
4. Adjust overlay thresholds in `config/thresholds.py` if business rules change.
5. Extend `tests/test_domain.py` and run the full quality gate.

---

## 10. Local troubleshooting

### Application issues

| Symptom | Action |
|---------|--------|
| Import errors | Confirm `pip install -e .` and active venv |
| UI layout regressions | Compare Gradio version with `pyproject.toml` constraint |
| Stale provider after `.env` change | Restart process (`reset_engine()` runs at startup) |

### Ollama issues

See [Ollama runbook](runbook-ollama.md). Set `OLLAMA_ENABLED=false` to isolate UI and domain logic from LLM dependencies.

---

## 11. IDE configuration

Point the interpreter to `.venv/bin/python`. Mark `telekom_profiler` as the source root if the IDE does not detect the editable install automatically.

---

## 12. Versioning and releases

| Source | Field |
|--------|-------|
| Package | `telekom_profiler.__version__` |
| Metadata | `pyproject.toml` → `[project].version` |
| History | `CHANGELOG.md` |

Bump version and changelog entries per team release policy before tagging.
