/* 双生 · 今日复习队列（FSRS 到期 + 错题复盘） */
(function () {
  'use strict';
  const { qs, esc, toastError } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let queue = null;
  let busy = false;

  function itemHtml(item, idx) {
    const isMistake = item.type === 'mistake';
    const icon = isMistake ? 'fact_check' : 'event_repeat';
    const cls = isMistake ? 'qk-amber' : 'qk-blue';
    const retention = item.retention == null ? '' : `<span class="chip">保持率 ${Math.round(item.retention * 100)}%</span>`;
    return `
<div class="card weak-card rise rise-${Math.min(5, idx + 1)}">
  <div class="wk-head">
    <div class="ot-ic ${cls}" style="width:38px;height:38px"><span class="i">${icon}</span></div>
    <h4>${esc(item.title)}</h4>
    <span class="chip ${item.priority >= 0.85 ? 'coral' : 'amber'}">优先级 ${Math.round(item.priority * 100)}</span>
  </div>
  <div class="wk-evi">${esc(item.detail || '')}</div>
  <div class="wk-next"><span class="i">assistant_direction</span><span>${esc(item.action || '')}</span></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
    ${retention}
    ${item.due_at ? `<span class="chip blue">到期 ${esc(new Date(item.due_at).toLocaleDateString())}</span>` : ''}
  </div>
  <button class="btn ${isMistake ? 'soft' : 'primary'} sm block" data-review="${esc(item.id)}">
    <span class="i" style="font-size:17px">${isMistake ? 'auto_awesome' : 'chat'}</span>${isMistake ? '去错题本复盘' : '复述这个知识点'}
  </button>
</div>`;
  }

  function render() {
    const box = qs('#review-body', root);
    if (busy) {
      box.innerHTML = `<div class="page-inner"><div class="card pad"><div class="skel" style="height:18px;width:60%;margin-bottom:12px"></div><div class="skel" style="height:13px;width:90%"></div></div></div>`;
      return;
    }
    if (!queue || !queue.length) {
      box.innerHTML = `<div class="page-inner"><div class="card"><div class="empty-box">
        <span class="i">verified</span><h4>今天没有到期复习</h4>
        <p>可以去错题本做一道探边题，继续给分身增加证据。</p>
      </div></div></div>`;
      return;
    }
    box.innerHTML = `<div class="page-inner">
      <div class="section-title rise rise-1"><span class="i">event_repeat</span>复习队列</div>
      ${queue.map(itemHtml).join('')}
      <div style="height:24px"></div>
    </div>`;
    root.querySelectorAll('[data-review]').forEach((btn) => {
      btn.onclick = () => {
        const item = queue.find((q) => q.id === btn.getAttribute('data-review'));
        if (!item) return;
        if (item.type === 'mistake') window.DSRouter.go('mistakes');
        else window.DSApp.startChatWith(`请检查我对「${item.title}」的复述，并指出遗漏点。`);
      };
    });
  }

  async function load() {
    const twin = store.activeTwin();
    if (!twin || busy) return;
    busy = true; render();
    try { queue = await api.getReviewQueue(twin.id, 20); }
    catch (err) { toastError(err); }
    busy = false; render();
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="review-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">今日复习 <span class="subtitle">FSRS 保持率 · 错题复盘</span></div>
  <button class="icon-btn primary" id="review-refresh"><span class="i">refresh</span></button>
</header>
<div class="page-body hide-scrollbar" id="review-body"></div>`;
    qs('#review-back', root).addEventListener('click', () => window.DSRouter.back());
    qs('#review-refresh', root).addEventListener('click', load);
  }

  function show() {
    if (!queue) load();
    else render();
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.review = { mount, show, invalidate() { queue = null; } };
})();
