# Development guide

## Prerequisites

- Python **3.10+**
- Git
- Optional: [Ollama](https://ollama.com) for LLM path

## Initial setup

```bash
git clone <repository-url>
cd telekom-personal-plan-recommender

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .          # editable install + console script

cp .env.example .env
ollama pull llama3.2      # if using default model
```

**Fedora:** `sudo dnf install python3-venv` if `venv` module is missing.

## Running the application

```bash
python app.py
# or
python -m telekom_profiler
# or (after pip install -e .)
telekom-profiler
```

Open the URL printed in the terminal (typically `http://127.0.0.1:7860`).

## Quality checks

```bash
# Unit tests
python -m unittest discover -s tests -v

# End-to-end sanity (imports, prompts, domain, UI build)
python scripts/sanity_check.py
```

Run both before opening a pull request.

## Project conventions

| Topic | Convention |
|-------|------------|
| Formatting | PEP 8, type hints on public APIs |
| Imports | Absolute imports from `telekom_profiler` |
| Strings | `from __future__ import annotations` in new modules |
| Config | Environment via `config/ollama_settings.py`; sliders in `config/sliders.py` |
| Paths | Use `telekom_profiler.paths`, not hard-coded relative paths |
| UI styling | `elem_classes` hooks in `ui/theme/app.css` |

## Adding a new profile provider

1. Implement `ProfileProvider` in a new module under `services/`:

```python
from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.services.protocols import ProfileProvider

class SegmentationApiProfileProvider:
    def profile(self, usage: CustomerUsage) -> ProfileResult:
        segment_id = call_your_api(usage)
        markdown = format_segment_markdown(segment_id)
        return ProfileResult(markdown=markdown, usage=usage, source="segmentation_api")
```

2. Wire into `ProfilerEngine`:

```python
engine = ProfilerEngine(profile_provider=SegmentationApiProfileProvider())
result = engine.profile(usage)
```

3. Add unit tests with mocked HTTP.

## Adding a new offer provider

Same pattern with `OfferProvider.recommend(profile, usage) -> str`.

## Modifying prompts

Templates live in `telekom_profiler/prompts/templates/`:

- `run_profile.md` — profile generation
- `run_offer.md` — offer generation

Placeholders use `{name}` syntax; filled in `prompts/builder.py`. After edits, run `scripts/sanity_check.py` to ensure no unfilled tokens remain.

## Modifying archetypes

1. Update `ARCHETYPE_CENTROIDS` in `domain/archetypes.py`.
2. Align `PROFILES` presets in `config/sliders.py`.
3. Update `data/consumer_archetypes.md` narrative.
4. Extend tests in `tests/test_domain.py`.

## Debugging Ollama

| Symptom | Fix |
|---------|-----|
| Connection refused | `ollama serve` |
| Model not found | `ollama pull <OLLAMA_MODEL>` |
| Timeout / runner start | Smaller model or `OLLAMA_ENABLED=false` |
| Slow responses | Shorter prompts, lower `num_predict`, GPU |

Set `OLLAMA_ENABLED=false` to isolate UI/domain issues from LLM.

## IDE setup

Point the interpreter to `.venv/bin/python`. The package is importable as `telekom_profiler` after `pip install -e .`.

## Versioning

Package version: `telekom_profiler.__version__` and `pyproject.toml` `[project].version`. Bump on release branches per team policy.
