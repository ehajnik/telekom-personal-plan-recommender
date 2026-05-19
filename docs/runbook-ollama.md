# Ollama operations runbook

Operational procedures for local LLM inference in the Private Customer Profiler. For environment variable definitions, see [Configuration](configuration.md). For architecture context, see [Architecture](architecture.md).

**Audience:** developers, workshop facilitators, platform support.

---

## 1. Service health checks

```bash
# API reachable?
curl -s http://localhost:11434/api/tags

# Model installed?
ollama list | grep -F "${OLLAMA_MODEL:-llama3.2}"

# Install default model if missing
ollama pull llama3.2
```

Ensure `ollama serve` is running when `OLLAMA_ENABLED=true`.

---

## 2. Configuration matrix

| Variable | Default | If misconfigured |
|----------|---------|------------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Start Ollama or correct service URL |
| `OLLAMA_MODEL` | `llama3.2` | `ollama pull <model>` |
| `OLLAMA_ENABLED` | `true` | Set `false` for rule-based-only operation |
| `OLLAMA_TIMEOUT` | `120` | Increase for large models on CPU |
| `OLLAMA_NUM_PREDICT` | `1024` | Reduce (e.g. `512`) to shorten latency |
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
INFO telekom_profiler.llm.client: Ollama completion ok model=llama3.2 duration_ms=...
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
