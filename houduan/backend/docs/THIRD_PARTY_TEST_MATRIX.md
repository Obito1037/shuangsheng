# EchoLearn 第三方能力测试矩阵

| 能力 | 测试输入 | 需要真实 AppKey | 当前自动化 | 返回字段覆盖 | 错误处理覆盖 | 备注 |
|---|---|---:|---|---|---|---|
| 静态结构 | P0 Provider/core 文件路径 | 否 | `test_provider_error_mapping.py` | 不适用 | 缺失文件会失败 | 验证核心文件存在 |
| 配置读取 | 空 env 文件 | 否 | `test_provider_error_mapping.py` | 不适用 | `missing_config` | 不依赖本地真实密钥 |
| 大模型同步 | `LlmMessage(role="user")` | 单元否，真实是 | `test_llm_provider.py` | `content/reasoning_content/provider/model/tokens/provider_request_id` | `invalid_request/missing_config/parse_failed` | 真实测试缺密钥时 skip |
| 大模型流式 | SSE `data:` 行 | 单元否，真实是 | `test_llm_provider.py` | 累计 `delta.content` 和 usage | 网络错误由 HTTP Client 统一映射 | 遇 `[DONE]` 正常结束 |
| 图片理解 | 本地 jpg + prompt | 是 | `test_llm_provider.py` | `description/provider/model/tokens` | 空 prompt、格式错误、模型不支持 | 真实测试使用 README 中可处理图片的 `Doubao-Seed-2.0-mini`；当前 `Volc-DeepSeek-V3.2` 返回模型不支持图片输入 |
| OCR | `tests/assets/ocr_test.jpg` | 单元否，真实是 | `test_ocr_provider.py` | `full_text/blocks/angle/provider` | `unsupported_format/missing_config/unknown_error` | 支持 `result.words` 和 `result.OCR` |
| 文本向量 | 两条短文本 | 单元否，真实是 | `test_embedding_provider.py` | `texts/vectors/dimension/provider/model` | `invalid_request/missing_config/parse_failed` | 校验维度一致 |
| 文本相似度 | query + 两条 sentences | 单元否，真实是 | `test_similarity_provider.py` | `query/sentences/scores/provider/model` | `invalid_request/missing_config/parse_failed` | 不限制分数范围 |
| 查询改写 | 当前 query + 一轮历史 | 单元否，真实是 | `test_query_rewrite_provider.py`, `tests/live/test_live_vivo_providers.py` | `original_query/rewritten_queries/provider` | `invalid_request/missing_config/content_blocked/provider_unavailable` | 当前真实 API 返回 `code=-3002`，映射为 `provider_unavailable` 并明确 skip，不伪造成成功；RAG 可使用原 query 继续 |
| 文本翻译 | 未接入 | 是 | 未实现 | 待定 | 待定 | P1 只记录 |
| Speech/Media | 目录和占位 Provider | 是 | 静态结构间接覆盖 | `SpeechCapabilityRecord/MediaCapabilityRecord` | 待定 | 当前阶段不实现真实调用 |

运行命令：

```powershell
cd backend
pytest tests/integrations/test_provider_error_mapping.py -s
pytest tests/integrations -s
```
