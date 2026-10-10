# Development guide

Engineering handbook for contributing to the Private Customer Profiler. For system design, see [Architecture](architecture.md). For runtime settings, see [Configuration](configuration.md).

---

## 1. Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| Python | 3.10 or later (matches `pyproject.toml`) |
| Git | Access to the corporate repository |
| Ollama | Optional; required only when `OLLAMA_ENABLED=true` |

---

## 2. Environment setup

```bash
git clone <repository-url>
cd telekom-personal-plan-recommender

./scripts/setup.sh    # creates .venv, installs -e ".[dev,ml]", copies .env.example → .env
# Or: make setup

source .venv/bin/activate
# Optional LLM path (default: qwen2.5:7b; tune timeout/tokens in .env for your hardware):
ollama serve
ollama pull qwen2.5:7b
```

For CPU-only hosts without a dedicated GPU, see [Ollama runbook § 8](runbook-ollama.md#8-cpu-only-workstations-no-dedicated-gpu). Use `OLLAMA_ENABLED=false` when you do not need LLM narratives.

The editable install (`pip install -e .`) registers the `telekom-profiler` console script and ensures imports resolve as `telekom_profiler`.

**Makefile shortcuts** (after `make setup`): `make run`, `make test`, `make lint`, `make typecheck`, `make sanity`, `make ml-train`, `make ml-evaluate`.

VS Code picks up `.venv` automatically via `.vscode/settings.json`.

Optional MOSTLY AI integration:

```bash
pip install -r requirements-mostlyai.txt
# Or: pip install -e ".[mostlyai]"
```

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

Pipeline is intentionally staged and not dynamic at runtime:

1. Generate a synthetic panel (+ ground-truth sidecar `<panel>.labels.csv`).
2. Train K-Means and freeze runtime artifacts.
3. Evaluate against the ground truth.
4. Commit data, labels and artifacts together.

```bash
python scripts/generate_synthetic_data.py --subscribers 1000 --seed 42
python scripts/subscriber_profiling.py \
  --input data/raw/private_mobile_usage_1000_subscribers_12_months.csv \
  --min-silhouette 0.5
python scripts/evaluate_model.py            # add --k-selection for the elbow/silhouette sweep
# or all three: make ml-train
```

**Synthetic generator.** Each subscriber draws a persistent personal baseline from its seed archetype's ranges (`ARCHETYPE_PARAMS` in `scripts/generate_synthetic_data.py`); months vary around it with log-normal noise, a personal relative trend (data −30…+45 %/year, voice −40…+15 %/year) and summer roaming seasonality. All subscribers are single-line B2C accounts.

When the generator or dataset changes, refresh the curated layer before committing:

1. `python scripts/evaluate_model.py --print-anchors` → `model.fixed_centroids` in `app_config.yaml`
2. Template slider positions and signatures in `telekom_profiler/ml/profile_characteristics.py`
3. Retrain and re-run the evaluation (it fails on accuracy < 90 %, a misclassified template or anchor drift > 25 %).

Inference is frozen between data refreshes (no dynamic runtime retraining).

Alternative generator path via MOSTLY AI:

```bash
# Trains MOSTLY AI on the latest seed panel under data/raw/ by default.
python scripts/generate_synthetic_data_mostlyai.py --subscribers 1000 --seed 42
python scripts/subscriber_profiling.py \
  --input data/raw/private_mobile_usage_mostlyai_1000_subscribers_12_months.csv
```

The MOSTLY AI workflow is optional and writes an engine workspace under `artifacts/mostlyai/`. It is intentionally separate from the baseline synthetic generator so CI and the default PoC path stay lightweight and deterministic.

| Output | Purpose |
|--------|---------|
| `data/raw/private_mobile_usage_*_subscribers_12_months.csv` | Monthly panel input |
| `data/raw/private_mobile_usage_*_subscribers_12_months.labels.csv` | Ground-truth seed archetype per subscriber (evaluation only; kept out of the training CSV) |
| `artifacts/kmeans.pkl`, `scaler.pkl` | Training artifacts (kept for compatibility/debugging) |
| `artifacts/label_map.json` | Cluster-index → profile-label map (required by `PROFILER_MODE=auto`) |
| `artifacts/profile_characteristics.json` | Profile labels and slider presets |
| `artifacts/cluster_features.json` | Ordered feature list used for scoring |
| `artifacts/frozen_centroids.json` | Runtime centroid/scaler data, per-cluster member means and training metadata |
| `artifacts/subscriber_features.csv` | Engineered subscriber-level features used for training |
| `artifacts/subscriber_cluster_map.csv` | Subscriber dropdown + per-cluster distances |

**Design rules:**

- `CLUSTER_FEATURES` contain only features computable from the six-slider input (`log_data_gb`, `log_voice_min`, `log_sms_count`, `log_roaming_days`), so batch and UI inference agree.
- Trend columns are excluded from `CLUSTER_FEATURES`; they feed overlays and offer sizing only. Units: data/voice in % per year.
- Named `PROFILE_LABELS` are mapped to clusters via Hungarian assignment against `LABEL_CANONICAL_CENTROIDS` (anchors in human units, mapped into the clustering space; an anchor with no clustering feature raises).
- Profile text/signatures/defaults are curated and hardcoded; they are not generated dynamically from cluster members.

Set `PROFILER_MODE=rules` to force legacy L1 archetypes (used in unit tests). Default `auto` selects ML when artifacts exist.

---

## 4.1 Measured accuracy

| Metric | Value |
|--------|-------|
| Batch accuracy (1000 subscribers) | 100 % |
| Slider/API-path accuracy | 100 % (previous 12-feature space: 76.8 %) |
| Hold-out panel (seed 7, 2000 subscribers) | 100 % |
| Silhouette, k = 5 (optimum over k = 2…9) | 0.56 |

The synthetic archetypes barely overlap, so these numbers validate the pipeline, not real-world accuracy. Evaluate on labelled production data before using segments for targeting.

## 4.2 Why the clustering space changed

The earlier feature set (12 features incl. session size, active days, plan tier, countries, session intensity) required imputing eight values from the sliders with hand-tuned formulas. `active_days_mean` was pure noise in the generator yet had a tiny scaler σ, so an imputation error of a few days dominated the distance. Restricting clustering to the observable usage levels (log-scaled) fixed slider-path accuracy without losing batch accuracy.

## 4.3 Why ML is operated as "generate -> define archetypes -> freeze"

The project intentionally avoids dynamic runtime retraining:

- Synthetic data generation is a required first step for this PoC pipeline.
- Archetypes are then defined from that generated dataset (AI-assisted and/or centroid-driven curation).
- Runtime inference uses frozen artifacts produced by that training pass.
- If synthetic data changes, clustering outcomes can change (including effective profile boundaries, and potentially profile count if `model.n_profiles` is revised), so archetype definitions and artifacts must be refreshed together.

Treat data refresh + archetype curation + artifact regeneration as one controlled maintenance event.

---

## 5. Quality assurance

Run the full gate locally before opening a pull request (mirrors CI):

```bash
export OLLAMA_ENABLED=false
export PROFILER_MODE=rules   # pin legacy archetypes so unit-test assertions stay deterministic when artifacts/ exists

python -m unittest discover -s tests -v
python scripts/sanity_check.py
python scripts/evaluate_model.py
ruff check telekom_profiler tests scripts
mypy telekom_profiler
```

| Check | Purpose |
|-------|---------|
| Unit tests | Domain logic, catalogue consistency, offer coverage, ML artifacts, providers, LLM client, prompts, models |
| `scripts/evaluate_model.py` | Segment accuracy vs synthetic ground truth, template round-trip, anchor drift |
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
| Configuration | Root config in `app_config.yaml`; env in `config/ollama_settings.py`; business rules in `config/thresholds.py` |
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
| Profile narratives | `data/consumer_archetypes.md` | Manual review |
| Tariff catalogue | `domain/catalog.py` + `data/plans_and_options.md` + `data/tariffs_private.md` | `tests/test_catalog.py` (SKUs, prices, allowances must match) |

**Updating prices or tariffs:** edit `domain/catalog.py` and both markdown files in the same change, update the "Stand" table and source links in `plans_and_options.md`, and run the unit tests.

Templates use `{placeholder}` syntax. After edits, run the sanity script to detect unfilled tokens.

---

## 9. Modifying archetypes and presets

ML profiles: see §4 (anchors, templates, retrain, evaluate). Legacy rules-mode archetypes:

1. Update `ARCHETYPE_CENTROIDS` in `domain/archetypes.py`.
2. Align `ui.profiles` in `app_config.yaml` for demo consistency.
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

This project uses **Semantic Versioning** with **[Conventional Commits](https://www.conventionalcommits.org/)** and **[Commitizen](https://commitizen-tools.github.io/commitizen/)**.

| Source | Field |
|--------|-------|
| Canonical version | `pyproject.toml` → `[project].version` |
| Runtime | `telekom_profiler.__version__` (from package metadata) |
| History | `CHANGELOG.md` (updated on `cz bump`) |
| Git tags | `v0.2.0`, `v0.3.0`, … |

While `major_version_zero` is enabled (default in `pyproject.toml`), **0.x** releases treat `feat` as a **minor** bump and `fix` as **patch** (per [SemVer](https://semver.org/) pre-1.0 guidance).

### Local release (maintainers)

```bash
pip install -e ".[dev]"
# Preview next version from commits since last tag
cz bump --dry-run
# Apply bump + CHANGELOG + git commit + tag
cz bump minor --yes   # or patch | major
git push origin main --tags
```

### GitHub Actions release

1. Ensure **CI** is green on `main`.
2. Run workflow **Release** (`.github/workflows/release.yml`) → choose `patch`, `minor`, or `major`.
3. The workflow runs `cz bump`, pushes the version commit, and pushes the `v*` tag.

### Before the first tag on a clone

If no `v*` tags exist yet, create the baseline tag once (already `0.2.0` in metadata):

```bash
git tag -a v0.2.0 -m "release: v0.2.0"
git push origin v0.2.0
```

Future bumps use `cz bump` only.
