# Local LLM FastAPI API

FastAPI service that wraps a local LLM provider and exposes OpenAI-compatible endpoints for remote calls.

Default backend is LM Studio OpenAI-compatible endpoint: `http://127.0.0.1:1234/v1`.

## Features

- OpenAI-like endpoints: `/v1/chat/completions`, `/v1/models`
- Streaming SSE support (`stream=true`)
- API key auth (`Authorization: Bearer <key>`)
- Basic rate limiting (per API key, requests/min)
- Structured JSON logging and `x-request-id`
- Health and readiness probes: `/healthz`, `/readyz`
- Prometheus metrics endpoint: `/metrics`
- Docker + Docker Compose + Nginx reverse proxy

## Project Structure

```
app/
  api/routes.py
  config.py
  infra/
  middleware/
  providers/
  services/
  schemas.py
  main.py
deploy/nginx.conf
```

## Quick Start (Local)

1. Create env file:
  - PowerShell: `Copy-Item .env.example .env`
2. Install uv (if not installed):
  - PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
3. Sync dependencies:
  - `uv sync`
4. Run server:
  - `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
5. Test health:
  - `curl http://127.0.0.1:8000/healthz`

## API Examples

### List models

```bash
curl -H "Authorization: Bearer dev-key-1" \
  http://127.0.0.1:8000/v1/models
```

### Non-stream chat completion

```bash
curl -X POST "http://127.0.0.1:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-1" \
  -d '{
    "model":"local-llm-7b",
    "messages":[{"role":"user","content":"你好，介绍一下你自己"}],
    "temperature":0.7,
    "max_tokens":128,
    "stream":false
  }'
```

### Stream chat completion (SSE)

```bash
curl -N -X POST "http://127.0.0.1:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-1" \
  -d '{
    "model":"local-llm-7b",
    "messages":[{"role":"user","content":"给我一句鼓励的话"}],
    "stream":true
  }'
```

## Production Notes

- Put Nginx/Caddy in front for HTTPS termination.
- Restrict API access with IP allowlist/security group.
- Backend adapter is configurable via `.env`:
  - `LLM_BACKEND=lmstudio_openai` (default)
  - `LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1`
  - `LMSTUDIO_API_KEY=` (optional)
- Configure process and model concurrency based on GPU memory.

