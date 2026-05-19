# Ollama runbook

Operational guide for local LLM inference in the Private Customer Profiler.

## Quick checks

```bash
# Server running?
curl -s http://localhost:11434/api/tags

# Model present?
ollama list | grep llama3.2

# Pull if missing
ollama pull llama3.2
```

## Environment variables

| Variable | Default | Action if wrong |
|----------|---------|-----------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Start `ollama serve` or fix URL |
| `OLLAMA_MODEL` | `llama3.2` | `ollama pull <model>` |
| `OLLAMA_ENABLED` | `true` | Set `false` for instant rule-based mode |
| `OLLAMA_TIMEOUT` | `120` | Increase if large models on CPU |
| `OLLAMA_NUM_PREDICT` | `1024` | Lower (e.g. `512`) for faster responses |
| `OLLAMA_FALLBACK_ON_ERROR` | `true` | Keep `true` for demos; `false` to surface errors |

## Symptom → fix

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Connection refused | Ollama not running | `ollama serve` |
| Model not found | Missing pull | `ollama pull $OLLAMA_MODEL` |
| Timeout / runner start | Model too large for RAM | Smaller model or higher `OLLAMA_TIMEOUT` |
| Slow profile + offer | Two sequential LLM calls | Lower `OLLAMA_NUM_PREDICT`; use rule-based for one step |
| Gradio traceback | Fallback disabled | Set `OLLAMA_FALLBACK_ON_ERROR=true` or `OLLAMA_ENABLED=false` |

## Disable LLM for demos

```env
OLLAMA_ENABLED=false
```

Restart the app. UI shows **Inference: rule-based**.

## Logs

With default `LOG_LEVEL=INFO`, successful completions log:

```
INFO telekom_profiler.llm.client: Ollama completion ok model=llama3.2 duration_ms=...
```

Fallback paths log warnings from `telekom_profiler.services.fallback`.

## Security note

Do not send MSISDN or account IDs in prompts. Usage aggregates only.
