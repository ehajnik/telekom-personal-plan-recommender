# Ollama operations runbook

Operational procedures for local LLM inference in the Private Customer Profiler. For environment variable definitions, see [Configuration](configuration.md). For architecture context, see [Architecture](architecture.md).

**Audience:** developers, workshop facilitators, platform support.

---

## 1. Service health checks

```bash
# API reachable?
curl -s http://localhost:11434/api/tags

# Model installed?
ollama list | grep -F "${OLLAMA_MODEL:-llama3.2:3b}"

# Install default model if missing
ollama pull llama3.2:3b
```

Ensure `ollama serve` is running when `OLLAMA_ENABLED=true`.

---

## 2. Configuration matrix

| Variable | Default | If misconfigured |
|----------|---------|------------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Start Ollama or correct service URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | `ollama pull <model>` |
| `OLLAMA_ENABLED` | `true` | Set `false` for rule-based-only operation |
| `OLLAMA_TIMEOUT` | `180` | Raise if a larger model still times out on CPU |
| `OLLAMA_NUM_PREDICT` | `2048` | Increase for longer narratives; decrease to shorten latency |
| `OLLAMA_FALLBACK_ON_ERROR` | `true` | Set `false` to surface errors to the UI |
| `LOG_LEVEL` | `INFO` | Set `DEBUG` for verbose client logging |

After changing `.env`, restart the application process.

---

## 3. Incident response

| Symptom | Probable cause | Resolution |
|---------|----------------|------------|
| Connection refused | Ollama not running | `ollama serve` or start platform service |
| Model not found | Image not pulled | `ollama pull $OLLAMA_MODEL` |
| Timeout / runner failed to start | Insufficient RAM or cold start | Smaller model, higher `OLLAMA_TIMEOUT`, or GPU |
| Slow end-to-end flow | Two sequential LLM calls (profile + offer) | Lower `OLLAMA_NUM_PREDICT`; disable LLM for one step |
| UI error with stack trace | Fallback disabled | `OLLAMA_FALLBACK_ON_ERROR=true` or `OLLAMA_ENABLED=false` |
| Inconsistent segments | LLM narrative drift | Use UI scoring panel and `ScoringResult` for ground truth |

---

## 4. Degraded operation modes

### 4.1 Rule-based only (recommended for demos and CI)

```env
OLLAMA_ENABLED=false
```

Restart the app. Header shows **Inference: rule-based**. No Ollama dependency.

### 4.2 LLM with automatic fallback (default)

```env
OLLAMA_ENABLED=true
OLLAMA_FALLBACK_ON_ERROR=true
```

On failure, providers return rule-based output; `source` may be `rule_based_fallback`. Warnings are logged from `telekom_profiler.services.fallback`.

### 4.3 Strict LLM (troubleshooting)

```env
OLLAMA_ENABLED=true
OLLAMA_FALLBACK_ON_ERROR=false
```

Use to validate gateway connectivity and prompt behaviour without masking errors.

---

## 5. Logging

With `LOG_LEVEL=INFO`, successful completions log:

```
INFO telekom_profiler.llm.client: Ollama completion ok model=llama3.2:3b duration_ms=...
```

Fallback activation logs warnings from `telekom_profiler.services.fallback`.

---

## 6. Security and data handling

- Do not include MSISDN, customer name, or account identifiers in prompts.  
- Pass usage aggregates only, consistent with internal AI usage policy.  
- For production, route inference through the approved corporate model gateway ([Integration](integration.md)).  

---

## 7. Escalation

| Level | Contact / action |
|-------|------------------|
| L1 | Verify Ollama service, model pull, `.env` flags per sections 1–4 |
| L2 | Application team — provider wiring, timeouts, fallback behaviour |
| L3 | AI platform team — gateway quotas, approved models, network egress |

---

## 8. CPU-only workstations (no dedicated GPU)

Segmentation and tariff logic do not use a GPU. Only optional Ollama narrative generation is affected.

### 8.1 Recommended setup

Copy `.env.example` (CPU-tuned defaults) and pull the configured model:

```bash
cp .env.example .env
ollama serve   # separate terminal
ollama pull llama3.2:3b
```

Default `.env` values:

```env
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=180
OLLAMA_NUM_PREDICT=2048
OLLAMA_FALLBACK_ON_ERROR=true
```

Each full UI flow runs **two** sequential LLM calls (profile, then offer). On CPU with `llama3.2:3b` each call typically completes in tens of seconds; lowering `OLLAMA_NUM_PREDICT` or disabling the LLM reduces wait time further.

### 8.2 Model selection

| Model tag | When to use |
|-----------|-------------|
| `llama3.2:3b` | Default; CPU-friendly (~2 GB on disk, fits in 8 GB RAM); default `OLLAMA_TIMEOUT=180` |
| `llama3.2:1b` | Tighter RAM or faster workshops; shorter / more generic narratives |
| `qwen2.5:3b`, `phi3:mini` | Alternatives with similar size class |
| `mistral-nemo:12b` | Strongest narrative quality, but needs ~16 GB RAM; raise `OLLAMA_TIMEOUT` (e.g. 600) and pre-warm with `ollama run mistral-nemo:12b ""` to avoid runner-start timeouts |
| `llama3:latest` (8B+) | **Not recommended** on CPU-only — timeouts and RAM pressure |

Deterministic archetype labels always come from `ScoringResult` in code/ML, not from the LLM ([ADR 001](adr/001-scoring-in-code.md)).

### 8.3 Rule-based only

```env
OLLAMA_ENABLED=false
```

No Ollama process required. Use for CI, offline development, or demos where narrative latency is unacceptable.
