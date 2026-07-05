/* 双生 · 错题本 2.0 + 做题流（真实 attempts / mistakes） */
(function () {
  'use strict';
  const { qs, esc, toast, toastError } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let mistakes = [];
  let weakPoints = [];
  let questions = [];
  let busy = false;
  let practiceQuestion = null;
  let showManual = false;

  const ERROR_TYPES = ['概念不清', '公式记错', '计算失误', '审题偏差', '方法选择错误', '步骤跳跃', '表达不完整'];

  function statusChip(status) {
    const map = {
      open: ['待复盘', 'coral'],
      reviewing: ['复盘中', 'amber'],
      resolved: ['已解决', 'mint'],
    };
    const item = map[status] || [status || 'open', 'outline'];
    return `<span class="chip ${item[1]}">${item[0]}</span>`;
  }

  function summaryHtml() {
    const open = mistakes.filter((m) => m.status === 'open').length;
    const reviewing = mistakes.filter((m) => m.status === 'reviewing').length;
    const resolved = mistakes.filter((m) => m.status === 'resolved').length;
    return `
<div class="weak-summary rise rise-1">
  <div class="card weak-cell"><b style="color:var(--coral)">${open}</b><span>待复盘</span></div>
  <div class="card weak-cell"><b style="color:var(--amber)">${reviewing}</b><span>复盘中</span></div>
  <div class="card weak-cell"><b style="color:var(--mint)">${resolved}</b><span>已解决</span></div>
</div>
${weakPoints.length ? `<div class="card pad rise rise-2" style="margin-top:12px">
  <div style="display:flex;gap:8px;align-items:flex-start">
    <span class="i" style="color:var(--primary);font-size:18px;margin-top:2px">track_changes</span>
    <p style="margin:0;font-size:var(--fs-sm);line-height:1.7;color:var(--ink-2)">
      当前薄弱点：${weakPoints.slice(0, 3).map((p) => esc(p.topic)).join('、')}
    </p>
  </div>
</div>` : ''}`;
  }

  function questionHtml() {
    if (!questions.length) {
      return `<div class="card pad rise rise-3">
        <p style="margin:0;color:var(--ink-3);font-size:var(--fs-sm);line-height:1.7">
          暂无诊断题。上传并解析资料后，系统会基于真实片段生成启动诊断题。
        </p>
      </div>`;
    }
    return `<div class="card rise rise-3" style="overflow:hidden">
      ${questions.slice(0, 5).map((q) => `
      <button class="out-item" data-practice="${esc(q.id)}" style="width:100%;text-align:left;border-bottom:1px solid var(--line)">
        <div class="ot-ic qk-blue"><span class="i">edit_note</span></div>
        <div class="ot-tx"><b>${esc(q.stem)}</b><span>难度 Elo ${Math.round(q.difficulty_elo || 1200)} · ${esc(q.source || 'diagnostic')}</span></div>
        <span class="i">chevron_right</span>
      </button>`).join('')}
    </div>`;
  }

  function manualHtml() {
    if (!showManual) return '';
    return `
<div class="card pad rise rise-2" id="manual-card" style="margin-top:12px">
  <div class="section-title" style="margin-top:0"><span class="i">add_task</span>录入错题</div>
  <textarea class="area" id="manual-source" rows="4" placeholder="题干、你的错误答案或错因片段"></textarea>
  <select class="input-shell" id="manual-error" style="width:100%;height:48px;margin-top:10px;border:1px solid var(--line-strong)">
    <option value="">暂不标注错因</option>
    ${ERROR_TYPES.map((t) => `<option value="${esc(t)}">${esc(t)}</option>`).join('')}
  </select>
  <button class="btn primary block" id="manual-submit" style="margin-top:12px"><span class="i">save</span>保存错题</button>
</div>`;
  }

  function mistakesHtml() {
    if (!mistakes.length) {
      return `<div class="card"><div class="empty-box">
        <span class="i">verified</span><h4>错题本是空的</h4>
        <p>答错的题会自动进入这里；也可以手动录入。</p>
      </div></div>`;
    }
    const groups = new Map();
    mistakes.forEach((m) => {
      const key = m.error_type || '待标注';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(m);
    });
    return Array.from(groups.entries()).map(([type, items], gi) => `
<div class="section-title rise rise-${Math.min(5, gi + 3)}"><span class="i">label</span>${esc(type)}</div>
${items.map((m, i) => `
<div class="card weak-card rise rise-${Math.min(5, gi + i + 3)}">
  <div class="wk-head">
    <h4>${esc((m.source_text || '错题').slice(0, 42))}${(m.source_text || '').length > 42 ? '…' : ''}</h4>
    ${statusChip(m.status)}
  </div>
  <div class="wk-evi">${esc(m.error_analysis || '简化模式：等待复盘补充错因。')}</div>
  <div class="wk-next"><span class="i">history_edu</span><span>${esc(m.source_text || '')}</span></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <button class="btn soft sm" data-variants="${esc(m.id)}"><span class="i" style="font-size:17px">auto_awesome</span>生成变式</button>
    <button class="btn soft sm" data-status="${esc(m.id)}" data-next="reviewing"><span class="i" style="font-size:17px">rate_review</span>复盘中</button>
  </div>
  <button class="btn ghost sm block" data-status="${esc(m.id)}" data-next="resolved" style="margin-top:10px"><span class="i" style="font-size:17px">check_circle</span>标记已解决</button>
</div>`).join('')}`).join('');
  }

  function practiceHtml() {
    const q = practiceQuestion;
    if (!q) return '';
    return `
<div class="page-inner">
  <div class="card pad rise rise-1">
    <div class="section-title" style="margin-top:0"><span class="i">edit_note</span>做题流</div>
    <h3 style="font-size:var(--fs-lg);line-height:1.55;margin:0 0 12px">${esc(q.stem)}</h3>
    ${q.options && q.options.length ? `<div class="evi-list" style="padding:0">${q.options.map((o) => `<div class="evi-item"><span class="i">radio_button_unchecked</span><span>${esc(o)}</span></div>`).join('')}</div>` : ''}
    <textarea class="area" id="practice-answer" rows="5" placeholder="写下你的答案或复述"></textarea>
    <div class="seg mode" id="practice-result" style="margin-top:12px">
      <div class="seg-thumb"></div>
      <button class="on" data-correct="true">答对</button>
      <button data-correct="false">答错</button>
    </div>
    <select class="input-shell" id="practice-rating" style="width:100%;height:48px;margin-top:10px;border:1px solid var(--line-strong)">
      <option value="good">感觉正常</option>
      <option value="easy">很轻松</option>
      <option value="hard">有点吃力</option>
      <option value="again">需要重来</option>
    </select>
    <select class="input-shell hidden" id="practice-error" style="width:100%;height:48px;margin-top:10px;border:1px solid var(--line-strong)">
      ${ERROR_TYPES.map((t) => `<option value="${esc(t)}">${esc(t)}</option>`).join('')}
    </select>
    <button class="btn primary block" id="practice-submit" style="margin-top:14px"><span class="i">send</span>提交并更新画像</button>
  </div>
  ${q.solution ? `<div class="card pad rise rise-2" style="margin-top:12px"><b>参考</b><p style="font-size:var(--fs-sm);color:var(--ink-2);line-height:1.7">${esc(q.solution)}</p></div>` : ''}
</div>`;
  }

  function render() {
    const box = qs('#wk-body', root);
    if (practiceQuestion) { box.innerHTML = practiceHtml(); bindPractice(); return; }
    if (busy) {
      box.innerHTML = `<div class="page-inner">
        <div class="weak-summary">
          ${[0, 1, 2].map(() => '<div class="card weak-cell"><div class="skel" style="height:30px;width:40px;margin:0 auto 8px"></div><div class="skel" style="height:12px;width:60px;margin:0 auto"></div></div>').join('')}
        </div>
        <div class="card pad" style="margin-top:12px"><div class="skel" style="height:18px;width:50%;margin-bottom:10px"></div><div class="skel" style="height:13px;width:90%"></div></div>
      </div>`;
      return;
    }
    box.innerHTML = `
<div class="page-inner">
  ${summaryHtml()}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px">
    <button class="btn primary" id="wk-start-practice"><span class="i">play_arrow</span>开始做题</button>
    <button class="btn ghost" id="wk-manual"><span class="i">add</span>录入错题</button>
  </div>
  ${manualHtml()}
  <div class="section-title rise rise-3"><span class="i">quiz</span>诊断/练习题</div>
  ${questionHtml()}
  <div class="section-title rise rise-4"><span class="i">fact_check</span>错题本</div>
  ${mistakesHtml()}
  <div style="height:24px"></div>
</div>`;
    bindList();
  }

  function bindList() {
    const start = qs('#wk-start-practice', root);
    if (start) start.onclick = () => {
      if (!questions.length) { toast('还没有可练习题，请先上传并解析资料', 'info'); return; }
      practiceQuestion = questions[0]; render();
    };
    const manual = qs('#wk-manual', root);
    if (manual) manual.onclick = () => { showManual = !showManual; render(); };
    const submitManual = qs('#manual-submit', root);
    if (submitManual) submitManual.onclick = submitManualMistake;
    root.querySelectorAll('[data-practice]').forEach((btn) => {
      btn.onclick = () => {
        practiceQuestion = questions.find((q) => q.id === btn.getAttribute('data-practice')) || null;
        render();
      };
    });
    root.querySelectorAll('[data-status]').forEach((btn) => {
      btn.onclick = () => updateStatus(btn.getAttribute('data-status'), btn.getAttribute('data-next'));
    });
    root.querySelectorAll('[data-variants]').forEach((btn) => {
      btn.onclick = () => generateVariants(btn.getAttribute('data-variants'));
    });
  }

  function bindPractice() {
    let isCorrect = true;
    const seg = qs('#practice-result', root);
    const errorSel = qs('#practice-error', root);
    seg.querySelectorAll('button').forEach((btn, idx) => {
      btn.onclick = () => {
        isCorrect = btn.getAttribute('data-correct') === 'true';
        seg.classList.toggle('pos-1', !isCorrect);
        seg.querySelectorAll('button').forEach((b, i) => b.classList.toggle('on', i === idx));
        errorSel.classList.toggle('hidden', isCorrect);
      };
    });
    qs('#practice-submit', root).onclick = () => submitPractice(isCorrect);
  }

  async function submitPractice(isCorrect) {
    const twin = store.activeTwin();
    if (!twin || !practiceQuestion) return;
    const answer = qs('#practice-answer', root).value.trim();
    const rating = qs('#practice-rating', root).value;
    const errorType = isCorrect ? null : qs('#practice-error', root).value;
    try {
      const result = await api.submitAttempt({
        twin_id: twin.id,
        question_id: practiceQuestion.id,
        is_correct: isCorrect,
        self_rating: rating,
        answer_text: answer,
        error_type: errorType,
      });
      const changes = (result.mastery_updates || []).map((u) => `${u.name} ${Math.round(u.before_p_mastery * 100)}%→${Math.round(u.after_p_mastery * 100)}%`).join('，');
      toast(changes ? `画像已更新：${changes}` : '做题记录已提交', 'ok');
      practiceQuestion = null;
      await load(true);
      const profileScreen = window.DSScreens.profile;
      if (profileScreen && profileScreen.invalidate) profileScreen.invalidate();
      const reviewScreen = window.DSScreens.review;
      if (reviewScreen && reviewScreen.invalidate) reviewScreen.invalidate();
      const homeScreen = window.DSScreens.home;
      if (homeScreen && homeScreen.invalidate) homeScreen.invalidate();
    } catch (err) { toastError(err); }
  }

  async function submitManualMistake() {
    const twin = store.activeTwin();
    const source = qs('#manual-source', root).value.trim();
    const errorType = qs('#manual-error', root).value || null;
    if (!twin || !source) { toast('先写下错题内容', 'info'); return; }
    try {
      await api.createMistake({ twin_id: twin.id, source_text: source, error_type: errorType });
      showManual = false;
      toast('错题已保存', 'ok');
      await load(true);
      const profileScreen = window.DSScreens.profile;
      if (profileScreen && profileScreen.invalidate) profileScreen.invalidate();
      const reviewScreen = window.DSScreens.review;
      if (reviewScreen && reviewScreen.invalidate) reviewScreen.invalidate();
      const homeScreen = window.DSScreens.home;
      if (homeScreen && homeScreen.invalidate) homeScreen.invalidate();
    } catch (err) { toastError(err); }
  }

  async function updateStatus(id, status) {
    try {
      await api.updateMistake(id, { status });
      toast(status === 'resolved' ? '已标记解决' : '已进入复盘中', 'ok');
      await load(true);
      const profileScreen = window.DSScreens.profile;
      if (profileScreen && profileScreen.invalidate) profileScreen.invalidate();
      const reviewScreen = window.DSScreens.review;
      if (reviewScreen && reviewScreen.invalidate) reviewScreen.invalidate();
      const homeScreen = window.DSScreens.home;
      if (homeScreen && homeScreen.invalidate) homeScreen.invalidate();
    } catch (err) { toastError(err); }
  }

  async function generateVariants(id) {
    try {
      const result = await api.generateMistakeVariants(id, 2);
      toast('已生成变式题，进入第一题', 'ok');
      await load(true);
      practiceQuestion = result.questions && result.questions[0] ? result.questions[0] : null;
      render();
    } catch (err) { toastError(err); }
  }

  async function load(force) {
    const twin = store.activeTwin();
    if (!twin || (busy && !force)) return;
    busy = true; render();
    try {
      const [m, q, w] = await Promise.all([
        api.listMistakes(twin.id).catch(() => []),
        api.getQuestions(twin.id, 'practice', 12).catch(() => []),
        api.getWeakPoints(twin.id).catch(() => []),
      ]);
      mistakes = m || [];
      questions = q || [];
      weakPoints = w || [];
    } catch (err) { toastError(err); }
    busy = false; render();
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="wk-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">错题本 <span class="subtitle">做题 · 错因 · 复盘</span></div>
  <button class="icon-btn primary" id="wk-refresh"><span class="i">refresh</span></button>
</header>
<div class="page-body hide-scrollbar" id="wk-body"></div>`;
    qs('#wk-back', root).addEventListener('click', () => {
      if (practiceQuestion) { practiceQuestion = null; render(); return; }
      window.DSRouter.back();
    });
    qs('#wk-refresh', root).addEventListener('click', () => load(true));
  }

  function show(params) {
    if (params && params.practice) practiceQuestion = params.practice;
    if (!mistakes.length && !questions.length && !busy) load(false);
    else render();
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.mistakes = { mount, show, invalidate() { mistakes = []; questions = []; weakPoints = []; practiceQuestion = null; } };
})();
