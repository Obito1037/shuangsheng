# 双生 · 完整升级计划（UI + 核心创意 + 算法）

> 版本：v1.0 · 2026-07-05
> 范围：基于当前仓库（`android-app/` WebView 前端 + `backend/` FastAPI 后端）的全量升级方案。
> 目标：把"训练学习分身 → 分身模拟试错 → 筛选最优路径 → 交付训练方案"这条核心创意真正做出来，同时把 UI 升级到有辨识度的成品水平。

---

## 目录

1. [现状诊断](#一现状诊断)
2. [核心创意的产品化拆解](#二核心创意的产品化拆解)
3. [总体架构升级](#三总体架构升级)
4. [数据模型设计](#四数据模型设计)
5. [算法设计（核心）](#五算法设计核心)
6. [后端接口改造](#六后端接口改造)
7. [前端重构与 UI 升级](#七前端重构与-ui-升级)
8. [分阶段落地路线](#八分阶段落地路线)
9. [测试与质量保障](#九测试与质量保障)
10. [风险与对策](#十风险与对策)

---

## 一、现状诊断

### 1.1 前端现状（android-app/app/src/main/assets/）

结构：单文件 `index.html`（约 2000 行，含全部页面与内联脚本）+ 三层运行时补丁：

| 文件 | 作用 | 问题 |
|---|---|---|
| `index.html` | 全部 10 个页面 + 基础 `app` 对象 | 页面内容大量硬编码演示数据（"已学习 12 份资料 / 发现 5 个薄弱点"、固定聊天气泡、固定路线 4 步、固定错题 2 条、黑板固定"步骤 2/5"） |
| `api-client.js` | API 客户端 + 学习路线/黑板渲染补丁 | 又一层对 `app.navigate` 的包装；MathJax 从 CDN 加载（违反离线约束，WebView 无网时黑板公式渲染失败） |
| `backend-bindings.js` | 猴子补丁重写 auth/侧栏/聊天/上传/导航 | 与 `api-client.js` 的补丁互相叠加：进入学习路线页时 `simulate` 被调用两次（一次渲染、一次丢弃结果）；`mistake-review` 页只调用了 `getWeakPoints` 但**从未渲染结果**，页面永远显示静态假数据 |
| `twin-scope-patch.js` | 再补一层 twin_id 透传 | 定时器轮询安装补丁，时序脆弱 |

结论：**"静态演示页 + 三层 monkey-patch"** 的架构已经到极限——每加一个功能都要绕过上一层补丁，UI 无法系统性升级，这是"UI 做不好看"的根本原因，不是调色问题。

### 1.2 后端现状（backend/app/）

真实可用的部分：

- 认证（邮箱验证码注册/登录/refresh/test-login）、用户、用量统计
- 分身 CRUD（用户隔离）、会话/消息落库、聊天走真实 LLM（vivo 网关，默认 `Doubao-Seed-2.0-mini`）
- 资料管线：上传 → `EnhancedDocumentService` 解析（txt/md/docx/pdf/图片 OCR）→ 分块 → m3e-base 向量 → twin 隔离检索（`retrieval_service.py`，embedding 优先、关键词兜底）→ 注入聊天 system prompt
- 分身模式 / 普通模式分离，RAG 只用该 twin 训练过的 chunk

**核心创意相关的部分全部是模板**（`app/services/twin_service.py`）：

| 能力 | 现状 | 差距 |
|---|---|---|
| `simulate_routes` 学习路径模拟 | 固定"路线 A/B/C"三个模板，分数 = 资料/消息计数的线性加权 | 没有学习者模型，没有模拟，没有真实的淘汰理由 |
| `weak_points` 薄弱点 | 两条固定话术 | 没有知识点、没有掌握度估计、没有错题数据 |
| `blackboard` 黑板讲解 | 三步通用套话，与主题无关 | 不调 LLM，无公式，无逐步推导 |
| 训练进度 `sync_percent` | 文件/消息计数堆百分比 | 不反映真实掌握状态 |
| 学习行为 `learning_records` | 裸事件日志（type+content） | 没有做题、判分、错因结构 |
| `chat/stream` | 直接调用非流式接口 | 假流式 |
| 口语英语 | `SpokenEnglishService.analyze` 直接抛错 | 未接 vivo ASR |

数据层缺失的实体：**知识点、题目、做题记录、错题、掌握度状态、学习计划/任务、复习排期**——这些是核心创意的地基，一个都没有。

### 1.3 其他问题

- `deploy.py` 把服务器 root 密码明文提交进了仓库（**安全事故，需立刻处理：改密码 + 从 git 历史清除**）。
- `houduan/`、`_repo_migration_backup/`、`tmp/reference-dualsheng/` 是历史副本，占仓库体积、易误改。
- 前端聊天无流式渲染、无 Markdown/LaTeX 渲染（分身答案里的公式显示为源码）。

---

## 二、核心创意的产品化拆解

把愿景翻译成四条可实现的产品主线，后续所有算法、接口、UI 都挂在这四条线上：

```
① 训练 Train      多模态资料 + 做题行为 + 对话  →  学习者画像（知识状态/错因模式/习惯）
② 模拟 Simulate   基于画像生成 N 条候选路径  →  在学习者模型上推演每条路径的预期收益
③ 筛选 Select     路径层：淘汰低收益路径并给出理由；题目层：挑选最能提升/暴露问题的题
④ 交付 Deliver    最优路径 + 任务清单（耗时/完成标准）+ 黑板讲解 + 错因复盘 + 下轮建议
```

关键设计立场：

1. **"分身"必须有可看见的内在状态。** 分身 = 学习者画像（每个知识点的掌握概率、遗忘曲线、错因分布、习惯偏好）+ 成长外观（等级/阶段/能力雷达）。没有内在状态，"模拟试错"就只能是话术。
2. **数字由算法给，叙事由 LLM 给。** 路径分数、淘汰理由、题目难度、复习时机全部来自可复算的模型（BKT/Elo/FSRS/效用函数），LLM 只负责把这些数字翻译成人话和生成内容（讲解、变式题、错因标注）。这保证结果诚实、可解释、可回归测试。
3. **证据不足时明确说。** 延续现有代码的诚实原则：冷启动阶段标注"基于启动方案"，不伪造精确数字。

---

## 三、总体架构升级

```
┌─ Android WebView（重构后）────────────────────────────────┐
│  screens/*.js 模块化页面 + store.js 单一状态源 + api.js    │
│  设计系统 tokens.css · KaTeX 本地化 · SSE 流式渲染          │
└──────────────────────────┬───────────────────────────────┘
                           │ REST + SSE
┌─ FastAPI ────────────────┴───────────────────────────────┐
│  api/…（twins/plans/questions/attempts/mistakes/review）  │
│  ┌────────── TwinBrain 编排层（新增）──────────────────┐   │
│  │ profile_service   学习者画像（聚合只读视图）          │   │
│  │ knowledge_graph   知识点抽取/图谱维护                │   │
│  │ mastery_service   BKT + Elo + FSRS 状态机            │   │
│  │ simulator         路径生成 → 蒙特卡洛推演 → 效用排序  │   │
│  │ selector          题目筛选（ZPD/信息增益/覆盖）        │   │
│  │ tutor             黑板讲解/错因标注/变式题/复盘 (LLM)  │   │
│  │ scheduler         复习队列（FSRS 到期计算）            │   │
│  └────────────────────────────────────────────────────┘   │
│  既有：chat / rag / retrieval / documents / speech         │
│  长任务（simulate、批量抽取）→ 后台线程 + 任务状态轮询       │
└──────────────────────────┬───────────────────────────────┘
                     SQLite（新增 9 张表，Alembic 迁移）
                     vivo 网关（LLM/Embedding/Rerank/OCR/ASR/TTS）
```

原则：不换技术栈（FastAPI + SQLite + WebView 保留），在 services 层内聚新增 `twin_brain/` 包；所有 LLM 输出经 pydantic JSON Schema 校验 + 一次修复重试 + 模板兜底（现有模板降级为兜底文案，不再是主路径）。

---

## 四、数据模型设计

新增表（Alembic 迁移，全部带 `user_id`/`twin_id` 隔离索引）：

```
knowledge_points   知识点
  id, twin_id, user_id, name, subject, parent_id(可空，树),
  description, source("llm_extract"|"manual"|"seed"), created_at

kp_edges           先修关系（图）
  id, twin_id, from_kp_id, to_kp_id, relation("prerequisite"|"related"), confidence

chunk_kp           资料块 ↔ 知识点 关联
  chunk_id, kp_id, weight

questions          题目（从资料抽取 / LLM 变式生成 / 用户录入错题）
  id, twin_id, user_id, kp_ids_json, stem, options_json(可空), answer,
  solution, source("extracted"|"variant"|"user_mistake"|"diagnostic"),
  difficulty_elo(初始 1200), disc_prior, embedding_json, created_at

attempts           做题记录（一切算法的燃料）
  id, user_id, twin_id, question_id, kp_ids_json, is_correct,
  self_rating("again"|"hard"|"good"|"easy" 可空), time_spent_sec,
  error_type(可空), answer_text, created_at

mistakes           错题本
  id, user_id, twin_id, question_id(可空), attempt_id(可空),
  source_text/source_image_file_id, error_type, error_analysis(LLM),
  status("open"|"reviewing"|"resolved"), variant_question_ids_json, created_at

mastery_states     掌握度状态（user × twin × kp 一行，算法核心状态）
  id, user_id, twin_id, kp_id,
  p_mastery FLOAT        -- BKT 掌握概率
  ability_elo FLOAT      -- 该 KP 上的能力分
  stability FLOAT        -- FSRS 记忆稳定性(天)
  difficulty_fsrs FLOAT  -- FSRS 难度 1..10
  last_review_at, due_at, attempt_count, correct_count, updated_at

study_plans        一次"模拟→筛选→交付"的完整产物
  id, user_id, twin_id, status("queued"|"simulating"|"ready"|"failed"),
  profile_hash,          -- 画像哈希，状态没变就复用不重算
  candidates_json,       -- 全部候选路径（含淘汰的+淘汰理由+分数明细）
  chosen_route_json, narrative(LLM 叙事), created_at, finished_at

plan_tasks         交付的任务清单
  id, plan_id, index, type("concept"|"practice"|"blackboard"|"recite"|"review"),
  title, detail, kp_ids_json, question_ids_json,
  est_minutes, completion_criteria, status("pending"|"active"|"done"|"skipped"),
  completed_at, outcome_json(正确率/用时等回填)

blackboard_lessons 黑板讲解缓存
  id, twin_id, topic, kp_id(可空), steps_json(LaTeX+讲解+自检问题),
  model, created_at
```

改造既有表：

- `learning_twins`：新增 `level INT`、`xp INT`、`profile_json`（错因分布/习惯偏好/口语水平等聚合画像），`sync_percent` 改为由 `mastery_states` 覆盖率与新鲜度计算。
- `learning_records`：保留为事件流（training feed），新增 `payload_json` 结构化字段。

---

## 五、算法设计（核心）

> 选型总原则：数据量小（单用户冷启动）、跑在 SQLite + CPU 上、每一步可解释。因此选 **BKT + Elo/IRT + FSRS + 蒙特卡洛效用模拟** 的组合，而不是需要大数据训练的 DKT/深度模型。所有参数可以先用文献默认值，后续用真实数据再校准。

### 5.1 知识点图谱构建（训练的第一步）

1. **种子分类**：按 twin.subject 内置一层粗分类（如数学→极限/导数/积分/级数…），存 `knowledge_points(source="seed")`。
2. **LLM 抽取**：资料解析完成后，对每个 document 的 chunk 批量调 LLM：`输入 chunk 文本 → 输出 {知识点名, 归属种子类, 先修猜测, 置信度}`（JSON Schema 校验）。同名/高相似（embedding 余弦 > 0.92）合并，写 `chunk_kp` 关联。
3. **错题/对话回填**：错因标注（5.4）和聊天中的提问也会命中或新建知识点，逐步把图谱织密。
4. 产物：分身的"知识版图"——UI 能力页直接可视化，也是后面一切估计的坐标系。

### 5.2 知识状态估计：BKT（掌握概率）

每个 (user, twin, kp) 维护标准 4 参数 BKT：

```
P(L0)=0.25  初始掌握概率（诊断测试后重置）
P(T) =0.20  每次有效练习后的学习转移概率
P(S) =0.10  会而做错（失误）
P(G) =0.20  不会而蒙对
```

每次 `attempt` 提交后贝叶斯更新：

```
答对: P(L|obs) = P(L)(1-P(S)) / [P(L)(1-P(S)) + (1-P(L))P(G)]
答错: P(L|obs) = P(L)P(S)     / [P(L)P(S) + (1-P(L))(1-P(G))]
然后: P(L) ← P(L|obs) + (1-P(L|obs))·P(T)
```

`p_mastery` 即分身对"你会不会这个点"的信念，直接驱动雷达图、薄弱点排序（`p_mastery < 0.6` 为薄弱）、以及模拟推演。

### 5.3 题目难度与能力：轻量 Elo/IRT

- 每题 `difficulty_elo` 初始 1200（LLM 可给 easy/medium/hard 先验 → 1050/1200/1350）；每个 (user, kp) 有 `ability_elo` 初始 1200。
- 预测正确率：`P(correct) = 1 / (1 + 10^((difficulty − ability)/400))`
- 每次做题后双向更新：`ability += K·(result − P)`，`difficulty −= K·(result − P)`，学生 K=32、题目 K=16（题目见多个 attempt 后逐渐收敛）。
- 作用：给**题目筛选**提供"这道题对当前的你有多难"的量化，弥补 BKT 不建模题目差异的缺点。

### 5.4 遗忘建模：简化 FSRS（复习排期）

每个 mastery_state 维护 `stability`（记忆稳定性，天）与 `difficulty_fsrs`：

```
可提取性: R(t) = (1 + t / (9·S))^(−1)     t=距上次复习天数
复习成功: S ← S · (1 + e^a · (11 − D) · S^(−b) · (e^(c·(1−R)) − 1))   （a,b,c 用 FSRS 默认参数）
复习失败: S ← S_fail(较小值，按 D 和 R 计算)
到期时间: due_at = last_review + S · 9·(1/0.9 − 1)  （目标保留率 90%）
```

产物：**今日复习队列**（`R < 0.9` 的 KP/错题排队），以及模拟器里的"遗忘风险"项——这是现在 UI 上"遗忘 低/中/高"标签的真实数据来源。

### 5.5 错因模式分析

1. 错题进入时（拍照 OCR / 做题答错 / 手动录入），调 LLM 按固定错因分类法标注：
   `概念不清 | 公式记错 | 计算失误 | 审题偏差 | 方法选择错误 | 步骤跳跃 | 表达不完整`
   输出：`{error_type, 涉及知识点, 一句话错因分析, 变式题建议}`。
2. 聚合到 `twin.profile_json.error_patterns`：每个 KP × 错因的频次分布。
3. 作用：路径模拟中"做题反推错因"策略的收益权重、变式题生成的靶向依据、复盘报告的素材。

### 5.6 学习路径模拟与筛选（核心创意的心脏）

**Step 1 生成候选**。六个策略原型，参数化实例化（不再是固定文案）：

| 原型 | 适用信号 |
|---|---|
| 概念先行（先补概念再刷题） | 薄弱 KP 的 p_mastery 低且错因以"概念不清"为主 |
| 做题反推（先做题再反推错因） | p_mastery 中等、attempt 样本少（需要暴露问题） |
| 黑板讲解 + 复述 | 概念型 KP、错因"步骤跳跃/表达不完整" |
| 诊断先行（先做诊断题再定计划） | 新 KP 覆盖率低 / 冷启动 |
| 薄弱点集中训练 | 存在 p_mastery < 0.5 的 KP 簇 |
| 变式探边（大量变式找能力边界） | p_mastery > 0.75 需要确认掌握边界 |

每个原型按当前画像实例化成具体步骤序列（每步 = {动作类型, 目标 KP, 题目难度带, 预计分钟数}），生成 4–6 条候选。

**Step 2 蒙特卡洛推演**。对每条候选路径，在学习者模型上滚动 N=200 次：

```
for 每次 rollout:
    state = 当前 mastery_states 的拷贝
    for 每个 step:
        按 Elo 预测 P(correct)，采样对/错
        用 BKT 公式更新 p_mastery；练习类 step 同时刷新 FSRS stability
    记录: Δ掌握 = Σ_kp w_kp·(p_after − p_before)   （薄弱 KP 权重高）
```

得到每条路径的 `E[Δ掌握]`、方差、总耗时、认知负荷（`load = mean(|difficulty − ability|/400)`，偏离 ZPD 越远负荷越高）、遗忘风险（路径结束时各 KP 的预测 R 值）。

**Step 3 效用排序与淘汰**：

```
U = 1.0·E[Δ掌握] + 0.3·薄弱点覆盖率 − 0.2·(耗时/时间预算) − 0.25·认知负荷 − 0.25·遗忘风险
```

最高分为推荐路径；其余标记淘汰，**淘汰理由从数字生成**（如"路线 B：预期掌握提升 +0.08 低于路线 A 的 +0.19，且认知负荷 0.71 偏高——题目难度超出你当前能力带"）。RNG 固定种子 = plan_id，保证同一份计划可复现、可测试。

**Step 4 LLM 叙事**：把推荐/淘汰的数字明细交给 LLM 生成给用户看的解释文案 + 每个任务的 title/完成标准措辞。数字不允许 LLM 改写（后端拼装时以模型数值为准）。

冷启动规则：`attempt_count 总和 < 10` 时跳过推演，直接推荐"诊断先行"路径并标注"当前为启动方案，完成诊断后将基于你的真实数据重新模拟"。

### 5.7 题目筛选算法

题库来源：资料抽取（LLM 把 chunk 转化为题目+KP 标签+难度先验）、错题变式（LLM 生成 2–3 道同源变式）、诊断题（每个种子 KP 预生成中等难度 1–2 题）。

选题打分（给定目标 KP 集合与任务类型）：

```
score(q) = ZPD 项:     1 − |P(correct|q) − p*|/0.5      p*=0.75（练习）/0.55（探边）
         + 信息增益项:  BKT 后验方差减少量（诊断任务权重最高）
         + 覆盖项:      命中薄弱 KP 数
         − 重复惩罚:    与近 7 天已做题 embedding 相似度 > 0.9 则重罚
```

这实现了愿景里的"哪些题最能暴露薄弱点、哪些题太简单收益低、哪些题太难负荷高"。

### 5.8 口语英语训练线

vivo ASR 转写（`vivo_asr_provider` 已有，接入 `SpokenEnglishService`）→ LLM 按 pronunciation/fluency/grammar/vocabulary 四维评分 + 逐句问题清单 → 生成复述任务进入 plan_tasks；口语表现按 KP（话题/句型）写入 attempts，同样走 BKT/FSRS。

### 5.9 LLM 编排层（TwinBrain.tutor）

统一收口所有 LLM 调用：提示词模板（诊断、路径叙事、黑板课、错因标注、变式题、复盘周报）+ pydantic 出参校验 + 失败一次修复重试 + 模板兜底 + 结果入库缓存（`blackboard_lessons`、`study_plans.narrative`）。缓存键 = `profile_hash`（画像未变不重新生成，控制 token 成本）。

---

## 六、后端接口改造

新增（全部挂在现有认证与 twin 隔离之下）：

| 接口 | 说明 |
|---|---|
| `POST /api/twins/{id}/diagnose` | 生成/获取诊断题组（冷启动入口） |
| `POST /api/attempts` | 提交做题结果 → 触发 BKT/Elo/FSRS 更新 + 错因管线 |
| `GET  /api/twins/{id}/profile` | 画像：雷达数据、KP 掌握列表、错因分布、成长事件、等级/XP |
| `POST /api/twins/{id}/plans` | 发起模拟（202 返回 plan_id，后台线程执行） |
| `GET  /api/plans/{plan_id}` | 轮询：simulating → ready（含候选/淘汰/推荐/任务） |
| `PATCH /api/plans/{plan_id}/tasks/{task_id}` | 任务完成回执（回填 outcome） |
| `GET  /api/twins/{id}/review-queue` | 今日复习队列（FSRS 到期） |
| `GET/POST /api/twins/{id}/mistakes` | 错题本 CRUD + `POST …/mistakes/{mid}/variants` 变式题 |
| `POST /api/twins/{id}/blackboard` | 升级：LLM 生成主题相关 LaTeX 分步讲解，缓存复用 |
| `POST /api/chat/stream` | 改为真 SSE 流式（provider 已有 stream 模型配置） |

`simulate` 响应契约示例（前端"模拟剧场"直接消费）：

```json
{
  "plan_id": "p_xxx", "status": "ready",
  "profile_summary": {"weak_kps": ["分部积分", "隐函数求导"], "attempts_used": 47},
  "candidates": [
    {"name": "概念先行", "utility": 0.62, "expected_gain": 0.19, "minutes": 25,
     "cognitive_load": 0.41, "forgetting_risk": 0.18, "eliminated": false,
     "reason": "薄弱点『分部积分』错因 71% 为概念不清，先补概念的模拟收益最高"},
    {"name": "做题反推", "utility": 0.44, "expected_gain": 0.08, "minutes": 18,
     "cognitive_load": 0.71, "forgetting_risk": 0.35, "eliminated": true,
     "reason": "题目难度带超出当前能力带 0.28，模拟中 62% 的 rollout 出现连续错误"}
  ],
  "chosen_route": {"name": "概念先行", "tasks": [
    {"index": 1, "type": "blackboard", "title": "分部积分：u 与 dv 的选取边界",
     "est_minutes": 8, "completion_criteria": "能复述 LIATE 顺序并说明两个反例"},
    {"index": 2, "type": "practice", "title": "靶向练习 3 题（难度带 0.70–0.85）",
     "question_ids": ["q1","q2","q3"], "est_minutes": 12,
     "completion_criteria": "3 题中至少 2 题独立做对"},
    {"index": 3, "type": "review", "title": "24 小时后复测入口已排入复习队列",
     "est_minutes": 5, "completion_criteria": "复测正确率 ≥ 80%"}
  ]},
  "narrative": "……(LLM 生成的推荐/淘汰解释)"
}
```

---

## 七、前端重构与 UI 升级

### 7.1 架构重构（先做，否则 UI 无从升级）

- 拆分 `index.html`：`css/tokens.css`（设计变量）+ `css/app.css`；`js/store.js`（单一状态 + 订阅渲染）、`js/api.js`（现 api-client 收编）、`js/screens/{auth,home,chat,simulate,plan,blackboard,mistakes,profile,library,settings}.js`。
- **删除三层 monkey-patch**：backend-bindings / twin-scope-patch 的逻辑并入对应 screen 模块；每页一个 `render(state)`，数据只从 store 走。
- 本地化 **KaTeX**（替换 CDN MathJax，体积小、可离线、渲染快），本地化 Tailwind 产物（构建期生成 `tailwind-local.css`，去掉 runtime JS）。
- 聊天接 SSE 流式 + 轻量 Markdown 渲染（自写 ~100 行解析器：标题/列表/粗体/代码/公式占位）。
- 保留 WebViewAssetLoader、appassets 域名、Android 返回键与语音桥接约定。

### 7.2 设计系统（解决"不好看"的系统性方案)

- **双主题气质**：日间"晨雾蓝"（现有品牌蓝降饱和，`#F7FAFD` 底 + `#0B8DE0` 主色 + 大量留白），夜间/黑板"深空"（`#12161C` 底 + 荧光粉笔色 `#7FD4FF/#FFD479`）。设置里可切换，黑板页恒用深空。
- **Tokens**：4/8/12/16/24/32 间距阶梯；圆角 12/20/28；阴影只留 2 档；字体沿用 Plus Jakarta Sans + 中文回退，字号阶梯 12/14/16/20/24/32。
- **动效语言**："分身是活的"——分身头像常态呼吸动画（scale 1↔1.03，4s）、数据更新时粒子脉冲、页面切换保持现有 240ms 缓动。全部 CSS 动画，禁 JS 逐帧。
- **组件库**：卡片、进度环、雷达图、时间线、任务项、骨架屏、空状态、toast 统一实现一份（`js/ui.js`），杜绝每页手拼。

### 7.3 关键页面重设计

1. **主页 = 分身状态中心**（替代现在的"空状态四宫格"）
   顶部：分身形象（按 level 有 4 个成长阶段外观：胚芽→成形→成熟→共生，SVG 分层）+ 等级/XP 条 + 一句当前状态（来自 profile）。
   中部：能力雷达（canvas，5–6 维取最重要 KP 簇）+ 今日三件事（复习队列 N 个到期 / 计划任务进行到第几步 / 新错题待复盘）。
   底部：进入聊天的 composer。**所有数字来自 `/profile` 与 `/review-queue`，删除一切硬编码。**

2. **模拟剧场（新页面，核心创意的舞台）**
   发起模拟后不是转圈，而是把后台真实阶段演出来：`读取画像 → 生成 6 条候选 → 推演 200 次 → 逐条淘汰（卡片变灰划线+理由浮出）→ 冠军路径高亮`。
   前端按 `GET /plans/{id}` 的阶段状态驱动分幕动画；ready 后展示完整对比表（收益/耗时/负荷/遗忘四维小条形图）。
   这是把"分身替你试错"从口号变成用户每次都能**看见**的过程。

3. **交付页（学习路线 2.0）**
   时间线保留但全部真实：每个任务卡带 `预计耗时`、`完成标准`、开始按钮；practice 任务点开进入做题流（题面/作答/自评四档），提交即 `POST /attempts`；完成后卡片回填正确率与用时，页尾出现"复盘 + 下一轮建议"。

4. **黑板 2.0**
   深空主题 + 粉笔质感（细噪点纹理叠加）；步骤逐条书写显现（CSS clip-path 揭示动画）；KaTeX 渲染公式；每步配自检问题，答完才点亮下一步；支持 vivo TTS 朗读讲解（可选）。

5. **错题本 2.0**
   入口：拍照（走 OCR）/ 从做题记录自动进入。列表按错因标签分组，卡片显示 LLM 错因分析；一键"生成变式题"进入做题流；状态流转 open→reviewing→resolved 有可视化（错题被"消灭"的动效）。

6. **能力页（新增）**
   KP 掌握列表（进度条 = p_mastery，颜色分带）；遗忘预警区（R 值将跌破 0.9 的 KP 倒计时）；错因分布环图；历史成长曲线。

7. **训练页（上传 2.0）**
   上传后展示真实管线各阶段：`缓存 → 解析 → 抽取知识点(+N 个) → 向量化 → 画像已更新`，各阶段状态来自 document.status 与新增的抽取任务状态；失败态如实显示（如"扫描版 PDF 需 OCR"）。

### 7.4 页面 ↔ 接口映射

| 页面 | 数据源 |
|---|---|
| 主页 | `/twins/{id}/profile` + `/review-queue` + `/plans?latest` |
| 模拟剧场 | `POST /plans` + 轮询 `/plans/{id}` |
| 交付页 | `/plans/{id}` + `PATCH tasks` + `POST /attempts` |
| 黑板 | `POST /blackboard`（缓存命中即秒开） |
| 错题本 | `/mistakes` + `/variants` + `POST /attempts` |
| 能力页 | `/profile`（含 mastery 明细） |
| 聊天 | `POST /chat/stream`（SSE） |

---

## 八、分阶段落地路线

> 每个里程碑独立可验收、可部署；M0 是其余一切的前提。

**M0 · 地基与止血（约 1 周）**
- 安全：立即更换服务器密码；`deploy.py` 改读环境变量；从 git 历史抹除凭据（filter-repo）；清理 `houduan/`、`_repo_migration_backup/`、`tmp/reference-dualsheng/`。
- 前端：完成 7.1 模块化重构（页面外观暂不变），KaTeX/Tailwind 本地化，SSE 流式聊天 + Markdown 渲染，`mistake-review` 页接通现有 weak-points 数据（消灭最后的假页面）。
- 后端：`/api/chat/stream` 真流式。
- 验收：assembleDebug 通过；断网可完整打开各页；同一操作不再重复调用 simulate；聊天逐字输出且公式正常渲染。

**M1 · 数据与画像（1–1.5 周）**
- 9 张新表迁移；attempts/mistakes/知识点抽取管线；`/profile`、`/attempts`、`/mistakes` 接口；BKT + Elo 更新器（先不含模拟）。
- 前端：能力页、错题本 2.0、做题流、训练页真实管线视图。
- 验收：上传一份 PDF 后能力页出现抽取的知识点；做 5 道题后 p_mastery 与雷达变化可见；错题打上错因标签。

**M2 · 算法核心（1.5–2 周）**
- FSRS 复习队列 + 到期推送入口；题目抽取/变式/诊断题生成；选题打分器；诊断流程（diagnose → attempts → 画像重置初值）。
- 前端：主页"今日三件事"、复习队列页、诊断引导（新分身首次进入）。
- 验收：新建分身 → 诊断 8 题 → 画像成形；次日复习队列出现到期项；选题命中 0.7–0.85 预测正确率带（用测试账号数据核验）。

**M3 · 模拟与交付（2 周）**
- simulator（候选生成 + 蒙特卡洛 + 效用排序）+ study_plans/plan_tasks 全链路 + LLM 叙事；黑板 2.0（LLM 生成 + 缓存）。
- 前端：模拟剧场、交付页 2.0、黑板 2.0。
- 验收：同一 plan_id 重放结果一致（种子固定）；淘汰理由与数字明细一致；完整走通"模拟→交付→做题→复盘→下一轮建议"闭环。

**M4 · 打磨与扩展（1 周）**
- 口语英语线（ASR+评分+复述任务）；TTS 黑板朗读；深色主题全局化；分身成长外观 4 阶段；性能与动效打磨；周报复盘（LLM）。
- 验收：口语上传出四维评分；主观走查 10 个页面无布局崩坏、无假数据残留。

---

## 九、测试与质量保障

- **算法单测（黄金数字）**：BKT/Elo/FSRS 更新公式各写定值用例（手算期望值断言）；模拟器固定种子回归测试；选题器 ZPD 带命中率测试。
- **契约测试**：新接口全部 pydantic response_model + pytest；LLM JSON 输出用录制 fixture 回放（沿用现有 `tests/fixtures/vivo` 模式）。
- **隔离测试**：A 用户/A 分身的题目、错题、画像对 B 不可见（延续现有 twin 隔离测试思路）。
- **前端**：assembleDebug 门禁；每页一份手工走查清单（空态/加载/错误/断网四态）；WebView 内存与掉帧抽查（成长动画页）。
- **降级演练**：关掉 vivo key 跑全流程，所有页面应显示诚实的降级文案而非假成功。

## 十、风险与对策

| 风险 | 对策 |
|---|---|
| `deploy.py` 密码已泄露在 git 历史 | **最高优先级**：改密码 → 历史清除 → 改用 env + SSH key |
| LLM JSON 不稳定 | Schema 校验 + 修复重试 + 模板兜底；兜底文案标注"简化模式" |
| Token 成本失控 | profile_hash 缓存；黑板/叙事入库复用；抽取批处理 |
| 冷启动没数据 | 诊断先行策略 + 默认先验 + 显式"启动方案"标注，不装懂 |
| SQLite 并发/长任务 | 模拟走后台线程 + 状态轮询；保持单 worker；未来量大再换 Postgres |
| 前端重构回归 | 按页迁移，旧文件保留到该页验收通过；M0 结束前新旧并存 |
| 算法参数不准 | 全部参数进配置表；先默认值上线，积累 attempts 后离线校准 |

---

### 附：本计划涉及的现有关键文件索引

- 前端：`android-app/app/src/main/assets/index.html`、`api-client.js`、`backend-bindings.js`、`twin-scope-patch.js`
- 后端模板逻辑（将被算法替换）：`backend/app/services/twin_service.py`
- RAG/检索（保留增强）：`backend/app/services/rag_service.py`、`retrieval_service.py`、`enhanced_document_service.py`
- 聊天（接流式）：`backend/app/services/chat_service.py`、`backend/app/api/chat.py`
- 口语（待接通）：`backend/app/services/spoken_english_service.py`、`backend/app/integrations/speech/*`
