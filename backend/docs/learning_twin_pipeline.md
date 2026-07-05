# 双生学习分身多模态训练与推荐路径设计

## 目标

双生的核心链路必须从演示型页面转为真实训练闭环：

```text
用户消息 / PDF / 图片 / 语音 / 英语口语
  -> 本地缓存
  -> 多模态解析
  -> 文本切块与向量索引
  -> RAG 检索
  -> 分身画像更新
  -> 路径候选生成
  -> 路径筛选与淘汰
  -> 黑板教学交付
```

## 采集层

必须采集并持久化以下数据：

1. 对话消息：用户消息、AI 回复、所属会话、所属分身、模式、时间。
2. 文档资料：PDF、Word、Markdown、TXT、PPT 等原始文件和解析文本。
3. 图片资料：原图、本地缓存路径、OCR 文本、图像理解摘要。
4. 语音资料：原始音频、转写文本、语速、停顿、发音问题、英语口语评分。
5. 学习行为：点击路径、完成任务、错题、复述、复测结果。

不能把静态示例数据伪装成用户数据。解析失败必须返回明确状态，例如 `parse_failed`、`ocr_pending`、`asr_pending`。

## 本地缓存

本地缓存分两层：

1. 原始文件缓存：保存上传文件、图片、语音。
2. 结构化缓存：保存解析文本、chunk、embedding、OCR 结果、转写文本、口语评分、分身记忆候选。

Android 端可以缓存最近会话、分身列表、上传队列和最近一次推荐路径；后端必须以数据库和本地文件存储为准。

## RAG 处理

资料进入 RAG 必须经过：

```text
extract_text -> split_chunks -> embed_chunks -> retrieve -> rerank -> answer_with_citations
```

图片资料走：

```text
image -> OCR + image understanding -> extracted_text -> chunks -> embeddings
```

语音资料走：

```text
audio -> ASR -> transcript -> oral scoring -> feedback chunks -> embeddings
```

英语口语评分至少需要输出：

```text
transcript
pronunciation_score
fluency_score
grammar_score
vocabulary_score
problem_segments
correction_plan
```

## 推荐学习算法

推荐学习路径不是固定模板。候选路径至少包括：

1. 概念澄清优先路径。
2. 直接训练刷题路径。
3. 黑板讲解 + 复述路径。
4. 资料回看 + 错因复盘路径。

每条路径评分由以下因素组成：

```text
expected_gain
cognitive_load
forgetting_risk
time_cost
source_evidence_score
weakness_match_score
recent_failure_penalty
oral_or_output_need
```

最终页面必须展示筛选过程。被淘汰路径要保留在页面中，并使用中横线表示淘汰，同时写明淘汰原因。

## 黑板教学交付

黑板教学不是静态 PPT。它应当是一个可播放、可分步、可交互的教学产物：

```text
step_index
title
narration
formula_latex
visual_layout
check_question
next_action
```

必须支持：

1. 长文本自动换行。
2. 数学公式 LaTeX 渲染。
3. 常见数学符号正常显示。
4. 公式块横向滚动或自动缩放。
5. 中文、英文、公式混排。

## 后端模型调用能力

后端 Provider 层需要逐步具备：

```text
LLM chat
streaming chat
query rewrite
embedding
rerank
OCR
image understanding
ASR
oral English scoring
LaTeX-aware explanation generation
structured JSON output generation
```

任何能力未配置时，必须显式返回 `provider_unavailable` 或 pending 状态，不能返回假结果。
