/* 双生 · 黑板讲解（深空主题 + 粉笔逐步书写 + KaTeX） */
(function () {
  'use strict';
  const { qs, esc, toast, toastError } = window.DSUi;
  const md = window.DSMarkdown;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let lesson = null;    // {topic, steps[]}
  let stepIdx = 0;
  let busy = false;
  let autoTimer = null;
  let ttsNoticeShown = false;

  function stopAuto() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    const btn = qs('#board-play', root);
    if (btn) btn.querySelector('.i').textContent = 'play_arrow';
  }

  function renderStep() {
    const box = qs('#board-stage', root);
    if (busy) {
      box.innerHTML = `<div class="board-loading"><span class="i">progress_activity</span><p>分身正在备课，整理讲解步骤…</p></div>`;
      return;
    }
    if (!lesson || !lesson.steps || !lesson.steps.length) {
      box.innerHTML = `<div class="board-loading"><span class="i" style="animation:none">cast_for_education</span>
        <p>输入一个主题，让分身在黑板上<br/>一步步推导给你看。</p></div>`;
      return;
    }
    const total = lesson.steps.length;
    stepIdx = Math.max(0, Math.min(stepIdx, total - 1));
    const step = lesson.steps[stepIdx];
    box.innerHTML = `
<div class="board-card">
  <div class="board-step-tag"><span class="i" style="font-size:15px">stylus_note</span>步骤 ${stepIdx + 1} / ${total}</div>
  <h2 class="board-title">${esc(step.title || '')}</h2>
  ${step.formula ? `<div class="board-formula"><div class="math-d" data-f="${esc(step.formula)}"></div></div>` : ''}
  <p class="board-explain">${esc(step.explanation || '')}</p>
  ${step.check_question ? `
  <div class="board-check"><div class="bc-q"><span class="i">contact_support</span><span>自检：${esc(step.check_question)}</span></div></div>` : ''}
</div>
<div class="board-nav">
  <button class="nav-btn" id="board-prev" ${stepIdx === 0 ? 'disabled' : ''}><span class="i">chevron_left</span></button>
  <div class="board-dots">${lesson.steps.map((_, i) => `<i class="${i === stepIdx ? 'on' : ''}"></i>`).join('')}</div>
  <button class="nav-btn" id="board-next" ${stepIdx === total - 1 ? 'disabled' : ''}><span class="i">chevron_right</span></button>
</div>`;

    // 公式渲染：优先 KaTeX；纯文字公式(含中文/→)则用粉笔字直接展示
    box.querySelectorAll('.math-d').forEach((el) => {
      const formula = el.getAttribute('data-f') || '';
      const looksLatex = /\\|\^|_|\{|\}/.test(formula) && !/[一-鿿]/.test(formula);
      if (looksLatex && window.katex) {
        try { window.katex.render(formula, el, { displayMode: true, throwOnError: false }); return; } catch (_) {}
      }
      el.textContent = formula;
    });

    const prev = qs('#board-prev', root);
    const next = qs('#board-next', root);
    if (prev) prev.onclick = () => { stopAuto(); stepIdx -= 1; renderStep(); };
    if (next) next.onclick = () => { stopAuto(); stepIdx += 1; renderStep(); };
    const sourceLabel = lesson.cached ? '缓存命中' : (lesson.evidence_mode || '');
    qs('#board-sub', root).textContent = [lesson.topic, sourceLabel].filter(Boolean).join(' · ');
  }

  async function load(topic) {
    const twin = store.activeTwin();
    if (!twin || busy) return;
    busy = true; stopAuto(); renderStep();
    try {
      const result = await api.getBlackboard(twin.id, topic || null);
      lesson = result;
      stepIdx = 0;
    } catch (err) { toastError(err); }
    busy = false; renderStep();
  }

  function toggleAuto() {
    const btn = qs('#board-play', root);
    if (autoTimer) { stopAuto(); return; }
    if (!lesson || !lesson.steps || lesson.steps.length < 2) return;
    btn.querySelector('.i').textContent = 'pause';
    requestTtsForCurrentStep();
    autoTimer = setInterval(() => {
      if (!lesson) { stopAuto(); return; }
      if (stepIdx >= lesson.steps.length - 1) { stopAuto(); return; }
      stepIdx += 1; renderStep();
      qs('#board-play', root).querySelector('.i').textContent = 'pause';
      requestTtsForCurrentStep();
    }, 7000);
  }

  async function requestTtsForCurrentStep() {
    if (!lesson || !lesson.steps || !lesson.steps[stepIdx]) return;
    const step = lesson.steps[stepIdx];
    const text = [step.title, step.explanation, step.check_question].filter(Boolean).join('\n');
    if (!text.trim()) return;
    try {
      const result = await api.synthesizeSpeech(text);
      if (result && result.status === 'pending' && !ttsNoticeShown) {
        ttsNoticeShown = true;
        toast('TTS 暂不可用，已自动播放步骤', 'info');
      }
    } catch (err) {
      if (!ttsNoticeShown) {
        ttsNoticeShown = true;
        toastError(err);
      }
    }
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="board-back"><span class="i">close</span></button>
  <div class="title">黑板讲解 <span class="subtitle" id="board-sub"></span></div>
  <button class="icon-btn" id="board-play"><span class="i">play_arrow</span></button>
</header>
<div class="board-body hide-scrollbar">
  <div class="board-inner">
    <div class="board-topic-row">
      <div class="input-shell">
        <span class="i" style="color:var(--chalk-dim)">search</span>
        <input id="board-topic" type="text" placeholder="输入想要讲解的主题，例如：拉普拉斯变换"/>
      </div>
      <button class="go" id="board-go"><span class="i">arrow_forward</span></button>
    </div>
    <div id="board-stage"></div>
  </div>
</div>`;
    qs('#board-back', root).addEventListener('click', () => { stopAuto(); window.DSRouter.back(); });
    qs('#board-play', root).addEventListener('click', toggleAuto);
    const go = () => { const t = qs('#board-topic', root).value.trim(); load(t || null); };
    qs('#board-go', root).addEventListener('click', go);
    qs('#board-topic', root).addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); go(); } });
  }

  function show() {
    if (!lesson) load(null);
    else renderStep();
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.blackboard = { mount, show, invalidate() { lesson = null; stepIdx = 0; } };
})();
