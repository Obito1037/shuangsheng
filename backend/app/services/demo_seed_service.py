from __future__ import annotations

"""测试账号演示数据：微积分学习分身 + 英语口语训练分身。

在 test_login 时幂等注入，用于决赛演示。所有数字状态（掌握度/Elo/FSRS/做题记录）
直接写入 twin_brain 状态表，保证画像页、复习队列、路径模拟开箱即有真实内容；
黑板讲解与路线叙事仍由线上 LLM 现场生成，不预置文案。
"""

import json
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.db.models.conversation import Conversation
from app.db.models.learning_twin import LearningTwin
from app.db.models.message import Message
from app.db.models.twin_brain import Attempt, KnowledgePoint, KpEdge, MasteryState, Mistake, Question
from app.db.models.user import User
from app.schemas.document import DocumentParseRequest
from app.services.enhanced_document_service import EnhancedDocumentService

logger = logging.getLogger(__name__)

CALCULUS_TWIN_NAME = "微积分学习分身"
ENGLISH_TWIN_NAME = "英语口语训练分身"

CALCULUS_NOTES = """微积分核心概念笔记

一、定积分的几何意义与性质
定积分 \\int_a^b f(x) dx 表示曲线 y=f(x) 与 x 轴在区间 [a,b] 上围成的有向面积。
当 f(x) 在区间上有正有负时，积分值是各部分面积的代数和，位于 x 轴上方的面积记为正、下方为负。
定积分的核心性质包括线性性、区间可加性以及积分中值定理。区间可加性指出对任意 c，
\\int_a^b = \\int_a^c + \\int_c^b，这在分段函数积分时尤其重要。积分中值定理说明存在一点 ξ
使得积分等于 f(ξ) 乘以区间长度，它是估计积分范围的常用工具。牛顿-莱布尼茨公式把定积分
和原函数联系起来，是全部计算的基础：若 F 是 f 的原函数，则积分等于 F(b)-F(a)。

二、分部积分法的选取策略
分部积分公式为 \\int u dv = uv - \\int v du，本质是乘积求导法则的逆运算。
选取 u 的经验顺序是 LIATE：对数函数、反三角函数、代数函数、三角函数、指数函数，排在前面的优先作为 u。
最常见的错误是把指数函数选作 u，导致 \\int v du 比原积分更复杂，越算越乱。
判断是否选对的标准很简单：分部一次之后剩下的积分应当变得更容易，否则就是选反了。
对于形如 x·eˣ、x·sin x、x·ln x 的乘积积分，几乎都可以用一次或两次分部解决。

三、泰勒展开与函数逼近
f(x) 在 x0 处的泰勒展开用多项式逼近函数，余项控制逼近误差，是分析局部行为的利器。
常见展开：eˣ = 1 + x + x²/2! + x³/3! + ...，收敛半径为无穷大；
sin x = x - x³/3! + x⁵/5! - ...；cos x = 1 - x²/2! + x⁴/4! - ...。
在求极限时，泰勒展开常常比反复使用洛必达更快，因为它一次性给出主导项和高阶无穷小。

四、洛必达法则的适用条件
洛必达法则只对 0/0 或 ∞/∞ 型未定式直接成立；使用前必须先验证确实是这两种未定式。
对于 0·∞、∞-∞、1^∞、0⁰、∞⁰ 等类型，必须先通过通分、取对数或变形转化成 0/0 或 ∞/∞ 才能使用。
每使用一次后要重新检查是否仍是未定式，若已不是就直接代入，否则会得到错误结论。

五、级数收敛判别方法
正项级数常用比值判别法：相邻项比值的极限小于 1 收敛，大于 1 发散，等于 1 时失效需换方法。
含 n! 或 nⁿ 的级数优先用比值判别法；含 n 次幂的级数适合用根值判别法。
比较判别法适合能找到简单参照级数（如 p 级数、几何级数）的情形。
交错级数则用莱布尼茨判别法：通项单调递减且趋于零即收敛。"""

CALCULUS_MISTAKE_NOTES = """错题摘录（第 3 次周测）

1. 计算 \\int x e^x dx 时，把 u 选成了 e^x，交换后积分复杂化，未能完成。
   正确路径：u=x, dv=e^x dx，一次分部即可得 (x-1)e^x + C。

2. 求 lim(x->0) (x - sin x)/x^3 时直接对分子分母各求了一次导就代入，
   实际上需要连续使用三次洛必达（或泰勒展开），答案 1/6。

3. 判断级数 \\sum n!/n^n 收敛性时误用比较判别法，应使用比值判别法，
   极限为 1/e < 1，级数收敛。"""

ENGLISH_NOTES = """口语练习素材：日常高频表达与纠错要点

一、问候与开场
自然的问候不止 How are you，可以用 How's it going、What have you been up to lately、
How's everything going。回答时避免机械的 I'm fine thank you and you，换成更真实的
Pretty good、Not bad、Been busy but good，会显得地道很多。开启话题时用 So、By the way
过渡，比直接抛出问题更自然。

二、过去经历叙述的时态
叙述昨天或过去发生、已经完成的动作，必须用一般过去时。最典型的中式错误是把动词留在原形：
Yesterday I go to the library 应改为 Yesterday I went to the library；
I study three hours 应改为 I studied for three hours。中文没有动词变形，所以一旦语速加快
就容易回退。练习方法是做过去时速答：听到中文场景，立刻用过去式完整句作答。

三、程度与喜好表达
very 不能直接修饰动词。I very like this movie 是错误的，应说 I really like this movie
或 I like it very much。表达强烈喜欢可以用 I'm really into it、I'm a big fan of it。
表达一般般用 It's okay、It's not really my thing。

四、观点表达句型
清晰表达观点的常用框架：From my perspective... 、I'd argue that... 、
The way I see it... 、If you ask me...。给理由时用 because、the reason is、
that's why 串联，结尾可以用 That's just my two cents 收束，听起来更完整、更有条理。

五、连读与弱读
口语中大量出现连读和弱读，这属于口语而非书面表达：want to 读成 wanna，
going to 读成 gonna，got to 读成 gotta，kind of 读成 kinda。
辅音结尾接元音开头会连读，如 an apple 听起来像 anapple。
练习时先慢速读准每个词，再逐步加速让它们自然连起来。"""


class DemoSeedService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_demo_data(self, user: User) -> None:
        """幂等：分身已存在则跳过。任何失败只记日志，不影响登录。"""
        try:
            if user.display_name == "Test User":
                user.display_name = "双生体验官"
                self.db.add(user)
            if not self._twin_by_name(user.id, CALCULUS_TWIN_NAME):
                self._seed_calculus(user)
            if not self._twin_by_name(user.id, ENGLISH_TWIN_NAME):
                self._seed_english(user)
            self.db.commit()
        except Exception:  # noqa: BLE001 - 演示数据失败不能挡住登录
            logger.exception("Demo seed failed; continuing without demo data")
            self.db.rollback()

    def _twin_by_name(self, user_id: str, name: str) -> LearningTwin | None:
        return self.db.scalar(
            select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.name == name)
        )

    # ---------- 微积分分身：数据丰富，已越过冷启动 ----------

    def _seed_calculus(self, user: User) -> None:
        now = utc_now()
        twin = LearningTwin(
            user_id=user.id,
            name=CALCULUS_TWIN_NAME,
            subject="数学",
            goal="期末微积分冲 90 分，重点补齐分部积分与洛必达的薄弱环节",
            stage="持续训练中",
            status="训练中 · 已索引资料并形成画像",
            sync_percent=76,
            level=5,
            xp=520,
            memories_json=json.dumps(
                [
                    "分部积分错因 71% 集中在 u 与 dv 选取",
                    "洛必达法则常忘记验证未定式条件",
                    "定积分几何意义掌握牢固，可作为讲解锚点",
                ],
                ensure_ascii=False,
            ),
        )
        self.db.add(twin)
        self.db.flush()

        kps = self._add_kps(
            user.id,
            twin.id,
            subject="数学",
            items=[
                ("定积分与几何意义", 0.82, 1268, 9.0, -2.0),
                ("分部积分法", 0.38, 1105, 1.6, 0.4),
                ("泰勒展开", 0.55, 1180, 3.2, 1.2),
                ("洛必达法则", 0.52, 1162, 2.4, -0.3),
                ("级数收敛判别", 0.61, 1201, 4.0, 2.5),
                ("微分方程初步", 0.45, 1150, 2.0, 5.0),
            ],
        )
        self._add_edges(user.id, twin.id, kps, [
            ("定积分与几何意义", "分部积分法"),
            ("泰勒展开", "洛必达法则"),
            ("定积分与几何意义", "微分方程初步"),
        ])

        calculus_items = [
                {
                    "stem": "计算不定积分 ∫ x·eˣ dx",
                    "kps": ["分部积分法"],
                    "answer": "(x-1)eˣ + C",
                    "solution": "取 u=x, dv=eˣdx，则 du=dx, v=eˣ。∫x·eˣdx = x·eˣ − ∫eˣdx = (x−1)eˣ + C。",
                    "elo": 1220.0,
                    "source": "extracted",
                },
                {
                    "stem": "求极限 lim(x→0) (x − sin x)/x³",
                    "kps": ["洛必达法则", "泰勒展开"],
                    "answer": "1/6",
                    "solution": "连续三次洛必达，或用 sin x 的泰勒展开 x − x³/6 + o(x³)，得极限 1/6。",
                    "elo": 1290.0,
                    "source": "extracted",
                },
                {
                    "stem": "判断级数 Σ n!/nⁿ 的敛散性",
                    "kps": ["级数收敛判别"],
                    "answer": "收敛",
                    "solution": "比值判别法：a(n+1)/a(n) → 1/e < 1，故级数收敛。",
                    "elo": 1265.0,
                    "source": "extracted",
                },
                {
                    "stem": "∫₀¹ (2x+1) dx 的值是多少？",
                    "kps": ["定积分与几何意义"],
                    "options": ["1", "2", "3", "4"],
                    "answer": "2",
                    "solution": "原函数 x²+x，代入上下限得 2。",
                    "elo": 1080.0,
                    "source": "diagnostic",
                },
                {
                    "stem": "下列哪种情形可以直接使用洛必达法则？",
                    "kps": ["洛必达法则"],
                    "options": ["0/0 型", "∞−∞ 型未变形", "0·∞ 型未变形", "1^∞ 型未变形"],
                    "answer": "0/0 型",
                    "solution": "只有 0/0 与 ∞/∞ 可以直接使用，其余需先变形。",
                    "elo": 1130.0,
                    "source": "diagnostic",
                },
                {
                    "stem": "写出 eˣ 在 x=0 处泰勒展开的前四项",
                    "kps": ["泰勒展开"],
                    "answer": "1 + x + x²/2 + x³/6",
                    "solution": "按 xⁿ/n! 逐项写出即可。",
                    "elo": 1175.0,
                    "source": "diagnostic",
                },
        ]
        questions = self._add_questions(user.id, twin.id, calculus_items, kps)

        # 12 条历史做题记录（越过冷启动阈值 10），错误集中在薄弱点
        history = [
            ("定积分与几何意义", True, "good", 95, None, 6),
            ("定积分与几何意义", True, "easy", 70, None, 6),
            ("分部积分法", False, "again", 260, "方法选择错误", 5),
            ("分部积分法", False, "hard", 300, "概念不清", 4),
            ("分部积分法", True, "hard", 240, None, 2),
            ("洛必达法则", False, "again", 210, "概念不清", 5),
            ("洛必达法则", True, "good", 150, None, 3),
            ("泰勒展开", True, "good", 180, None, 4),
            ("泰勒展开", False, "hard", 260, "步骤跳跃", 2),
            ("级数收敛判别", True, "good", 160, None, 3),
            ("级数收敛判别", False, "hard", 280, "方法选择错误", 1),
            ("微分方程初步", False, "again", 240, "概念不清", 1),
        ]
        kp_question = {}
        for question in questions:
            for kp_id in json.loads(question.kp_ids_json):
                kp_question.setdefault(kp_id, question)
        for kp_name, correct, rating, seconds, error_type, days_ago in history:
            kp = kps[kp_name]
            question = kp_question.get(kp.id) or questions[0]
            self.db.add(
                Attempt(
                    user_id=user.id,
                    twin_id=twin.id,
                    question_id=question.id,
                    kp_ids_json=json.dumps([kp.id]),
                    is_correct=correct,
                    self_rating=rating,
                    time_spent_sec=seconds,
                    error_type=error_type,
                    answer_text="（演示历史作答）",
                    created_at=now - timedelta(days=days_ago, hours=kp.name.__len__() % 5),
                )
            )

        self._add_mistakes(
            user.id,
            twin.id,
            [
                {
                    "source_text": "∫ x·eˣ dx：我把 u 选成 eˣ、dv 选成 x dx，结果 ∫v du 变成 ∫(x²/2)eˣdx 更复杂，没做出来。",
                    "error_type": "方法选择错误",
                    "analysis": "分部积分 u 的选取应遵循 LIATE 顺序，代数函数 x 应优先于指数函数 eˣ 作为 u。属于策略性错误而非计算失误。",
                    "status": "open",
                    "question": kp_question.get(kps["分部积分法"].id),
                },
                {
                    "source_text": "lim(x→0)(x−sin x)/x³ 我只用了一次洛必达就代入 x=0，得到 0，和答案 1/6 对不上。",
                    "error_type": "步骤跳跃",
                    "analysis": "一次求导后仍是 0/0 型，需要继续使用洛必达直至未定式消除；或改用泰勒展开一步到位。",
                    "status": "reviewing",
                    "question": kp_question.get(kps["洛必达法则"].id),
                },
                {
                    "source_text": "判断 Σ n!/nⁿ 收敛性时用比较判别法比较 1/n²，比不出来。",
                    "error_type": "方法选择错误",
                    "analysis": "含 n! 与 nⁿ 的级数应首选比值判别法；比较判别法找不到合适的参照级数。已在复测中做对。",
                    "status": "resolved",
                    "question": kp_question.get(kps["级数收敛判别"].id),
                },
            ],
        )

        self._add_conversation(
            user=user,
            twin=twin,
            title="分部积分到底怎么选 u",
            turns=[
                (
                    "user",
                    "∫x·eˣdx 这种题我总是把 u 选错，有没有稳定的判断方法？",
                ),
                (
                    "assistant",
                    "有的，按 LIATE 顺序选 u：对数 > 反三角 > 代数 > 三角 > 指数。\n\n"
                    "你的错题里 71% 都是把指数函数选成了 u。这道题里 x 是代数函数、eˣ 是指数函数，"
                    "所以 u=x，dv=eˣdx：\n\n$$\\int x e^x dx = x e^x - \\int e^x dx = (x-1)e^x + C$$\n\n"
                    "验证方式：分部一次后积分应当变简单；变复杂就说明选反了。要不要我出两道变式题验证？",
                ),
                ("user", "好，顺便把这个知识点排进今天的路线。"),
                (
                    "assistant",
                    "已加入。当前画像里「分部积分法」掌握度 0.38，是最优先的薄弱点；"
                    "我会在学习路线里安排：黑板讲解（8 分钟）→ 2 道变式题（12 分钟）→ 24 小时后复测。"
                    "完成后掌握度预计提升到 0.55 以上。",
                ),
            ],
            base_time=now - timedelta(days=1, hours=3),
        )

        self._add_documents(
            user_id=user.id,
            twin_id=twin.id,
            docs=[
                ("微积分核心概念笔记.md", CALCULUS_NOTES),
                ("第3次周测错题摘录.md", CALCULUS_MISTAKE_NOTES),
            ],
        )
        self._prune_auto_artifacts(
            user_id=user.id,
            twin_id=twin.id,
            keep_kp_ids={kp.id for kp in kps.values()},
            keep_question_ids={q.id for q in questions},
        )

    # ---------- 英语口语分身：冷启动阶段，演示诊断先行 ----------

    def _seed_english(self, user: User) -> None:
        now = utc_now()
        twin = LearningTwin(
            user_id=user.id,
            name=ENGLISH_TWIN_NAME,
            subject="英语",
            goal="日常口语流利度提升，纠正中式表达和时态错误",
            stage="持续训练中",
            status="训练中 · 已形成口语画像",
            sync_percent=58,
            level=3,
            xp=360,
            memories_json=json.dumps(
                [
                    "口语中一般过去时经常回退为现在时",
                    "程度副词搭配存在中式直译（very like）",
                ],
                ensure_ascii=False,
            ),
        )
        self.db.add(twin)
        self.db.flush()

        kps = self._add_kps(
            user.id,
            twin.id,
            subject="英语",
            items=[
                ("过去经历叙述（时态）", 0.35, 1120, 1.4, 0.2),
                ("程度与喜好表达", 0.42, 1140, 1.8, 1.0),
                ("观点表达句型", 0.50, 1170, 2.6, 3.0),
                ("连读与弱读", 0.30, 1100, 1.2, -0.5),
            ],
        )

        english_items = [
                {
                    "stem": "用英语描述你昨天做过的三件事（注意时态）",
                    "kps": ["过去经历叙述（时态）"],
                    "answer": "went / had / met 等过去式",
                    "solution": "叙述已完成的过去动作用一般过去时：Yesterday I went to the lab, had a group meeting, and met my advisor.",
                    "elo": 1150.0,
                    "source": "diagnostic",
                },
                {
                    "stem": "翻译成地道英语：我非常喜欢这部电影。",
                    "kps": ["程度与喜好表达"],
                    "answer": "I really like this movie.",
                    "solution": "very 不能直接修饰动词 like；用 really / very much：I really like it 或 I like it very much。",
                    "elo": 1120.0,
                    "source": "diagnostic",
                },
                {
                    "stem": "用两种句型表达你对网课的看法",
                    "kps": ["观点表达句型"],
                    "answer": "From my perspective... / I'd argue that...",
                    "solution": "示例：From my perspective, online classes offer flexibility. I'd argue that self-discipline matters more.",
                    "elo": 1180.0,
                    "source": "diagnostic",
                },
                {
                    "stem": "朗读：I want to go to the gym（注意 want to 连读）",
                    "kps": ["连读与弱读"],
                    "answer": "wanna",
                    "solution": "口语中 want to 弱读为 wanna，going to 弱读为 gonna。",
                    "elo": 1110.0,
                    "source": "diagnostic",
                },
        ]
        questions = self._add_questions(user.id, twin.id, english_items, kps)

        # 11 条记录（越过冷启动阈值 10 → 已训练分身，可演示真实画像与路线模拟）
        history = [
            ("过去经历叙述（时态）", False, "again", 120, "表达不完整", 6),
            ("过去经历叙述（时态）", False, "hard", 100, "概念不清", 5),
            ("过去经历叙述（时态）", True, "hard", 90, None, 2),
            ("程度与喜好表达", False, "hard", 80, "表达不完整", 5),
            ("程度与喜好表达", True, "good", 70, None, 3),
            ("程度与喜好表达", True, "good", 65, None, 1),
            ("观点表达句型", True, "good", 90, None, 4),
            ("观点表达句型", True, "easy", 75, None, 1),
            ("连读与弱读", False, "again", 60, "概念不清", 3),
            ("连读与弱读", False, "hard", 70, "表达不完整", 2),
            ("连读与弱读", True, "hard", 80, None, 1),
        ]
        kp_question = {}
        for question in questions:
            for kp_id in json.loads(question.kp_ids_json):
                kp_question.setdefault(kp_id, question)
        for kp_name, correct, rating, seconds, error_type, days_ago in history:
            kp = kps[kp_name]
            question = kp_question.get(kp.id) or questions[0]
            self.db.add(
                Attempt(
                    user_id=user.id,
                    twin_id=twin.id,
                    question_id=question.id,
                    kp_ids_json=json.dumps([kp.id]),
                    is_correct=correct,
                    self_rating=rating,
                    time_spent_sec=seconds,
                    error_type=error_type,
                    answer_text="（口语演示作答）",
                    created_at=now - timedelta(days=days_ago, hours=2),
                )
            )

        self._add_mistakes(
            user.id,
            twin.id,
            [
                {
                    "source_text": "口语练习原句：Yesterday I go to the library and study three hours.",
                    "error_type": "概念不清",
                    "analysis": "叙述昨天发生的动作应使用一般过去时 went / studied；中文没有动词时态变化，这是典型迁移错误。",
                    "status": "open",
                    "question": kp_question.get(kps["过去经历叙述（时态）"].id),
                },
                {
                    "source_text": "口语练习原句：I very like this movie.",
                    "error_type": "表达不完整",
                    "analysis": "very 不能修饰动词；改为 I really like this movie 或 I like it very much。",
                    "status": "reviewing",
                    "question": kp_question.get(kps["程度与喜好表达"].id),
                },
            ],
        )

        self._add_conversation(
            user=user,
            twin=twin,
            title="昨天的口语练习复盘",
            turns=[
                ("user", "帮我复盘昨天的口语练习，我感觉时态又出问题了。"),
                (
                    "assistant",
                    "复盘完成，昨天 8 句口语样本里有 3 处时态回退：\n\n"
                    "1. \"Yesterday I go to the library\" → went\n"
                    "2. \"I study three hours\" → studied for three hours\n"
                    "3. \"She tell me...\" → told\n\n"
                    "规律：一旦语速加快，动词就回到原形。建议今天做 5 分钟「过去时速答」训练：我说中文场景，你用过去时快速回答。现在开始吗？",
                ),
                ("user", "开始吧。"),
                (
                    "assistant",
                    "第一题：昨天晚饭你吃了什么？用完整句子回答。（提示：had / ate）",
                ),
            ],
            base_time=now - timedelta(hours=20),
        )

        self._add_documents(
            user_id=user.id,
            twin_id=twin.id,
            docs=[("口语练习素材_日常高频表达.md", ENGLISH_NOTES)],
        )
        self._prune_auto_artifacts(
            user_id=user.id,
            twin_id=twin.id,
            keep_kp_ids={kp.id for kp in kps.values()},
            keep_question_ids={q.id for q in questions},
        )

    # ---------- 共用工具 ----------

    def _add_kps(self, user_id: str, twin_id: str, *, subject: str, items) -> dict[str, KnowledgePoint]:
        now = utc_now()
        kps: dict[str, KnowledgePoint] = {}
        for name, p_mastery, elo, stability, due_days in items:
            kp = KnowledgePoint(user_id=user_id, twin_id=twin_id, name=name, subject=subject, source="seed")
            self.db.add(kp)
            self.db.flush()
            kps[name] = kp
            self.db.add(
                MasteryState(
                    user_id=user_id,
                    twin_id=twin_id,
                    kp_id=kp.id,
                    p_mastery=p_mastery,
                    ability_elo=elo,
                    stability=stability,
                    difficulty_fsrs=6.5 - p_mastery * 3,
                    last_review_at=now - timedelta(days=max(1, int(stability))),
                    due_at=now + timedelta(days=due_days),
                    attempt_count=3,
                    correct_count=max(1, int(p_mastery * 3)),
                )
            )
        return kps

    def _add_edges(self, user_id: str, twin_id: str, kps: dict[str, KnowledgePoint], pairs) -> None:
        for from_name, to_name in pairs:
            if from_name in kps and to_name in kps:
                self.db.add(
                    KpEdge(
                        user_id=user_id,
                        twin_id=twin_id,
                        from_kp_id=kps[from_name].id,
                        to_kp_id=kps[to_name].id,
                        relation="prerequisite",
                        confidence=0.8,
                    )
                )

    def _add_questions(self, user_id: str, twin_id: str, items, kps: dict[str, KnowledgePoint]) -> list[Question]:
        questions: list[Question] = []
        for item in items:
            kp_ids = [kps[name].id for name in item.get("kps", []) if name in kps]
            question = Question(
                user_id=user_id,
                twin_id=twin_id,
                kp_ids_json=json.dumps(kp_ids),
                stem=item["stem"],
                options_json=json.dumps(item.get("options"), ensure_ascii=False) if item.get("options") else None,
                answer=item.get("answer", ""),
                solution=item.get("solution", ""),
                source=item.get("source", "diagnostic"),
                difficulty_elo=item.get("elo", 1200.0),
            )
            self.db.add(question)
            questions.append(question)
        self.db.flush()
        return questions

    def _add_mistakes(self, user_id: str, twin_id: str, items) -> None:
        for item in items:
            question = item.get("question")
            self.db.add(
                Mistake(
                    user_id=user_id,
                    twin_id=twin_id,
                    question_id=question.id if question is not None else None,
                    source_text=item["source_text"],
                    error_type=item["error_type"],
                    error_analysis=item["analysis"],
                    status=item.get("status", "open"),
                )
            )

    def _add_conversation(self, *, user: User, twin: LearningTwin, title: str, turns, base_time) -> None:
        conversation = Conversation(user_id=user.id, twin_id=twin.id, title=title)
        self.db.add(conversation)
        self.db.flush()
        for index, (role, content) in enumerate(turns):
            message = Message(
                user_id=user.id,
                twin_id=twin.id,
                conversation_id=conversation.id,
                role=role,
                content=content,
                provider="vivo" if role == "assistant" else None,
                model="Doubao-Seed-2.0-mini" if role == "assistant" else None,
            )
            message.created_at = base_time + timedelta(minutes=index * 2)
            self.db.add(message)

    def _prune_auto_artifacts(
        self,
        *,
        user_id: str,
        twin_id: str,
        keep_kp_ids: set[str],
        keep_question_ids: set[str],
    ) -> None:
        """资料解析会自动抽取知识点/诊断题；无 key 兜底可能产生 LaTeX 碎片。

        演示分身的画像必须确定可控，因此只保留本服务显式创建的知识点与题目。
        仅作用于演示分身，用户现场创建的分身不受影响。
        """
        from app.db.models.twin_brain import ChunkKnowledgePoint

        junk_kps = list(
            self.db.scalars(
                select(KnowledgePoint).where(
                    KnowledgePoint.twin_id == twin_id,
                    KnowledgePoint.user_id == user_id,
                    KnowledgePoint.id.not_in(keep_kp_ids),
                )
            )
        )
        junk_kp_ids = {kp.id for kp in junk_kps}
        if junk_kp_ids:
            for model, column in (
                (MasteryState, MasteryState.kp_id),
                (ChunkKnowledgePoint, ChunkKnowledgePoint.kp_id),
            ):
                for row in self.db.scalars(select(model).where(column.in_(junk_kp_ids))):
                    self.db.delete(row)
            for edge in self.db.scalars(
                select(KpEdge).where(
                    (KpEdge.from_kp_id.in_(junk_kp_ids)) | (KpEdge.to_kp_id.in_(junk_kp_ids))
                )
            ):
                self.db.delete(edge)
            for kp in junk_kps:
                self.db.delete(kp)
        for question in self.db.scalars(
            select(Question).where(
                Question.twin_id == twin_id,
                Question.user_id == user_id,
                Question.id.not_in(keep_question_ids),
            )
        ):
            self.db.delete(question)
        self.db.flush()

    def _add_documents(self, *, user_id: str, twin_id: str, docs) -> None:
        service = EnhancedDocumentService(self.db)
        for title, text in docs:
            try:
                service.parse(
                    user_id=user_id,
                    payload=DocumentParseRequest(text=text, title=title, twin_id=twin_id),
                )
            except Exception:  # noqa: BLE001 - 单份资料失败不影响其余种子
                logger.exception("Demo document parse failed: %s", title)
