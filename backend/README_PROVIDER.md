# EchoLearn Provider Layer

This backend folder contains the third-party AI capability provider layer for EchoLearn. It is intentionally limited to provider abstractions, vivo provider implementations, schemas, error mapping, config loading, and local tests.

## Required Local Environment

Create `backend/.env` with real credentials only on the local machine:

```env
VIVO_APP_ID=your_app_id
VIVO_APP_KEY=your_app_key
VIVO_BASE_URL=https://api-ai.vivo.com.cn
VIVO_LLM_BASE_URL=https://api-ai.vivo.com.cn/v1
VIVO_LLM_MODEL=Doubao-Seed-2.0-mini
VIVO_LLM_TEXT_MODEL=Doubao-Seed-2.0-mini
VIVO_LLM_STREAM_MODEL=Doubao-Seed-2.0-mini
VIVO_IMAGE_UNDERSTANDING_MODEL=Doubao-Seed-2.0-mini
VIVO_REASONING_MODEL=Doubao-Seed-2.0-mini
VIVO_VISION_MODEL=Volc-DeepSeek-V3.2
VIVO_EMBEDDING_MODEL=m3e-base
VIVO_RERANK_MODEL=bge-reranker-large
HTTP_TIMEOUT_SECONDS=30
HTTP_MAX_RETRIES=2
HTTP_BACKOFF_SECONDS=0.25
```

`backend/.env` is ignored by git. Do not put real credentials in source files, docs, tests, Android code, or README files.

## Run Tests

```powershell
cd backend
pip install -r requirements.txt
pytest tests/integrations/test_provider_error_mapping.py -s
pytest tests/integrations -s
```

The error-mapping tests do not need real credentials. Real provider API tests run when `backend/.env` contains real `VIVO_APP_ID` and `VIVO_APP_KEY`; otherwise they are skipped with an explicit reason.

## Reuse From Services

Business services should depend on the base interfaces, for example `LlmProvider`, `EmbeddingProvider`, or `QueryRewriteProvider`, and receive one concrete implementation through dependency wiring. Services should consume only schemas from `app/schemas/*` and catch only `ProviderError`.

Prefer `app.integrations.registry.create_provider_registry()` as the business-facing entry point. It returns abstract providers and keeps concrete vivo classes behind the registry boundary.

Use `python scripts/check_capabilities.py` to inspect configured capability metadata and live-test status without printing secrets.
