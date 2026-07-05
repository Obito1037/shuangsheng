# EchoLearn 第三方能力映射

README.md 已按 UTF-8 读取并分析。当前阶段只实现 P0 Provider 层，并通过 `app/integrations/capabilities.py` 维护 capability registry。状态字段含义：

- `implemented`: 已有可调用 Provider 实现。
- `documented_only`: README 已记录但当前阶段不实现。
- `android_side`: 端侧 SDK 能力，不属于后端 Provider。
- `provider_unavailable`: 已发起真实调用但供应商当前不可用。
- `live_test_passed`: 当前 live 测试已通过。
- `live_test_failed`: 当前 live 测试失败；供应商不可用但被明确 skip 时不记为失败。

| 能力 | 类型 | README.md 接口/协议 | Provider 文件 | 统一返回模型 | implemented | documented_only | android_side | provider_unavailable | live_test_passed | live_test_failed | 优先级 | 备注 |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 大模型 API | 云端 API | `POST /v1/chat/completions` | `app/integrations/llm/vivo_llm_provider.py` | `LlmMessageResult` | true | false | false | false | true | false | P0 | 文本模型配置：`VIVO_LLM_TEXT_MODEL` |
| 大模型流式 | 云端 API | `POST /v1/chat/completions` with `stream=true` | `app/integrations/llm/vivo_llm_provider.py` | `LlmMessageResult` | true | false | false | false | true | false | P0 | 流式模型配置：`VIVO_LLM_STREAM_MODEL` |
| 图片理解 | 云端 API | `POST /v1/chat/completions` with `image_url` | `app/integrations/llm/vivo_llm_provider.py`, `app/integrations/vision/vivo_image_understanding_provider.py` | `ImageUnderstandingResult` | true | false | false | false | true | false | P0 | 图片模型配置：`VIVO_IMAGE_UNDERSTANDING_MODEL`，避免使用当前不支持图片输入的 `Volc-DeepSeek-V3.2` |
| 通用 OCR | 云端 API | `POST /ocr/general_recognition` | `app/integrations/vision/vivo_ocr_provider.py` | `OcrResult` | true | false | false | false | true | false | P0 | 支持 jpg/png/bmp |
| 文本向量 | 云端 API | `POST /embedding-model-api/predict/batch` | `app/integrations/embedding/vivo_embedding_provider.py` | `EmbeddingResult` | true | false | false | false | true | false | P0 | 支持 `m3e-base`、`bge-base-zh-v1.5` |
| 文本相似度 | 云端 API | `POST /rerank` | `app/integrations/similarity/vivo_similarity_provider.py` | `SimilarityResult` | true | false | false | false | true | false | P0 | 不假设分数范围 |
| 查询改写 | 云端 API | `POST /query_rewrite_base` | `app/integrations/query_rewrite/vivo_query_rewrite_provider.py` | `QueryRewriteResult` | true | false | false | true | false | false | P0 | 真实调用当前返回 `code=-3002`，映射为 `provider_unavailable`；RAG 可用原 query 降级 |
| 文本翻译 | 云端 API | `POST /translation/query/self` | 待建 | 待建 | false | true | false | false | false | false | P1 | 当前只记录 |
| 实时短语音识别 | 云端 API WebSocket | `ws://api-ai.vivo.com.cn/asr/v2` | `app/integrations/speech/vivo_asr_provider.py` | `SpeechCapabilityRecord` | false | true | false | false | false | false | P1 | 当前只保留目录和记录 |
| 长语音听写 | 云端 API WebSocket | 长语音实时转文本协议 | `app/integrations/speech/vivo_lasr_provider.py` | `SpeechCapabilityRecord` | false | true | false | false | false | false | P1 | 当前只记录 |
| 长语音转写 | 云端 API HTTP | 录音文件长语音转写分阶段接口 | `app/integrations/speech/vivo_lasr_provider.py` | `SpeechCapabilityRecord` | false | true | false | false | false | false | P1 | 当前只记录 |
| TTS 音频生成 | 云端 API | README.md `TTS/音频生成` 协议 | `app/integrations/speech/vivo_tts_provider.py` | `SpeechCapabilityRecord` | false | true | false | false | false | false | P1 | 当前只记录 |
| 图片生成 | 云端 API | `POST /api/v1/image_generation` | `app/integrations/media/vivo_image_generation_provider.py` | `MediaCapabilityRecord` | false | true | false | false | false | false | P2 | 当前只记录 |
| 视频生成 | 云端 API | `POST /api/v1/submit_task` and query task | `app/integrations/media/vivo_video_generation_provider.py` | `MediaCapabilityRecord` | false | true | false | false | false | false | P2 | 当前只记录 |
| 方言自由说 | 云端 API WebSocket | 方言短语音转文本协议 | 待建 | 待建 | false | true | false | false | false | false | P2 | 当前只记录 |
| 同声传译 | 云端 API WebSocket | 同声传译协议 | 待建 | 待建 | false | true | false | false | false | false | P2 | 当前只记录 |
| 声音复刻 | 云端 API | README.md 声音复刻服务 | 待建 | 待建 | false | true | false | false | false | false | P3 | 当前只记录 |
| 地理编码/POI | 云端 API | README.md 能力表列出，接口待后续抽取 | 待建 | 待建 | false | true | false | false | false | false | P3 | 当前只记录 |
| 端侧 LLM | Android 端侧 SDK | C++/Java SDK, local model files | 不属于后端 Provider | 不适用 | false | true | true | false | false | false | 端侧 | Android SDK 能力，不暴露后端 AppKey |
| 端侧文本审核 | Android 端侧 SDK | `CmsLocalFrame.TextModeration` | 不属于后端 Provider | 不适用 | false | true | true | false | false | false | 端侧 | Android SDK 能力 |

