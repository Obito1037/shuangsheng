# EchoLearn 第三方 Provider 设计

## 为什么要有 Provider

EchoLearn 的业务 Service 不应该知道 vivo、OpenAI 或其他供应商的请求参数、鉴权方式、错误码和原始 JSON。Provider 层把供应商差异封装在 `app/integrations/*` 内部，对业务层只暴露稳定的 EchoLearn schema。

当前调用关系：

```text
Android 客户端 -> EchoLearn 后端 API -> 业务 Service -> 第三方能力 Provider -> 第三方 API
```

## 为什么不能让 Android 直接调用第三方 API

真实 `AppId/AppKey` 必须只存在于后端运行环境的 `backend/.env` 中。若 Android 直接调用第三方 API，密钥会进入客户端包、日志或网络调试环境，无法安全轮换，也无法在服务端统一做限流、审计、错误映射和供应商替换。

## Provider、Schema、Error、HttpClient 的关系

`app/core/config.py` 统一读取 `.env` 和环境变量，并在缺少 `VIVO_APP_ID` 或 `VIVO_APP_KEY` 时抛 `ProviderError(missing_config)`。

`app/core/http_client.py` 统一添加 `Authorization: Bearer AppKey`、`request_id/requestId`、timeout 和日志脱敏；网络异常和 HTTP 错误统一转成 `ProviderError`。

`app/core/errors.py` 定义稳定错误类型。对外只返回 `safe_message`，`raw_error` 只保留给本地调试，不返回给 Android。

`app/schemas/*` 定义 EchoLearn 内部稳定模型。Provider 必须解析第三方响应，并返回这些 schema，不允许把第三方原始 JSON 直接传出。

`app/integrations/*/base.py` 定义能力抽象。`vivo_*_provider.py` 是当前供应商实现。

`app/integrations/registry.py` 是业务层入口。业务 Service 后续通过 `ProviderRegistry.get_llm_provider()`、`get_ocr_provider()`、`get_embedding_provider()`、`get_similarity_provider()`、`get_query_rewrite_provider()` 获取抽象 Provider，不直接依赖 `Vivo*Provider`。

`app/integrations/capabilities.py` 维护 capability registry，字段包括 `provider`、`default_model`、`supports_streaming`、`supports_image`、`requires_app_id`、`requires_app_key`、`implemented`、`documented_only`、`android_side`、`provider_unavailable`、`live_test_passed`、`live_test_failed`。

模型路由拆分为四个独立配置项：`VIVO_LLM_TEXT_MODEL`、`VIVO_LLM_STREAM_MODEL`、`VIVO_IMAGE_UNDERSTANDING_MODEL`、`VIVO_REASONING_MODEL`。图片理解 Provider 会优先使用 `VIVO_IMAGE_UNDERSTANDING_MODEL`，避免把不支持图片输入的文本模型用于图片理解。

## 后续如何替换供应商

替换供应商时新增同一 base interface 的实现，例如 `openai_llm_provider.py` 或 `another_embedding_provider.py`。业务 Service 继续依赖 `LlmProvider`、`EmbeddingProvider` 等抽象，返回模型仍使用 `LlmMessageResult`、`EmbeddingResult` 等 schema，因此 Android 和业务 API 不需要感知供应商差异。

## 当前 P0 Provider 职责

| Provider | 职责 |
|---|---|
| `VivoLlmProvider` | 封装 `/v1/chat/completions`，支持同步、流式、图片理解的底层调用 |
| `VivoImageUnderstandingProvider` | 作为 vision 层适配器复用 LLM 图片理解 |
| `VivoOcrProvider` | 本地图片校验、base64 编码、调用 `/ocr/general_recognition` 并解析 OCR 块 |
| `VivoEmbeddingProvider` | 调用 `/embedding-model-api/predict/batch`，校验向量数量和维度 |
| `VivoSimilarityProvider` | 调用 `/rerank`，校验 score 数量与 sentences 一致 |
| `VivoQueryRewriteProvider` | 组装 README.md 的 `prompts` 格式，处理 `code=0/-9` 和错误码；`code=-3002` 映射为 `provider_unavailable`，RAG 可捕获后使用原 query 降级 |
