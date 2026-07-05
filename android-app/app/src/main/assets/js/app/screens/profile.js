/* 双生 · 能力页（M1 学习者画像） */
(function () {
  'use strict';
  const { qs, esc, twinAvatarHtml, toastError } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let profile = null;
  let questions = [];
  let busy = false;

  function pct(value) { return Math.max(0, Math.min(100, Math.round((value || 0) * 100))); }
  function statusLabel(status) {
    return ({ new: '待诊断', weak: '薄弱', growing: '成长中', stable: '较稳' })[status] || '待诊断';
  }
  function statusCls(status) {
    return ({ new: 'outline', weak: 'coral', growing: 'amber', stable: 'mint' })[status] || 'outline';
  }

  function masteryHtml(items) {
    if (!items || !items.length) {
      return `<div class="card"><div class="empty-box">
        <span class="i">radar</span><h4>还没有知识点画像</h4>
        <p>上传资料并解析后，分身会先用简化模式抽取知识点；做题后这里会显示 BKT 掌握概率。</p>
      </div></div>`;
    }
    return items.map((m) => `
<div class="card pad profile-kp">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
    <h4 style="margin:0;font-size:var(--fs-md);flex:1">${esc(m.name)}</h4>
    <span class="chip ${statusCls(m.status)}">${statusLabel(m.status)}</span>
  </div>
  <div class="thin-track"><i style="width:${pct(m.p_mastery)}%"></i></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
    <span class="chip blue">掌握 ${pct(m.p_mastery)}%</span>
    <span class="chip">Elo ${Math.round(m.ability_elo || 1200)}</span>
    <span class="chip">练习 ${m.attempt_count || 0} 次</span>
  </div>
</div>`).join('');
  }

  function errorsHtml(items) {
    if (!items || !items.length) return '<div class="card pad"><p style="margin:0;color:var(--ink-3)">暂无错因分布。答错的 attempt 会自动进入错题本。</p></div>';
    const total = items.reduce((sum, item) => sum + item.count, 0) || 1;
    return `<div class="card pad">
      ${items.map((item) => `
      <div style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;font-size:var(--fs-sm);margin-bottom:6px"><b>${esc(item.error_type)}</b><span>${item.count}</span></div>
        <div class="thin-track"><i style="width:${Math.round(item.count / total * 100)}%;background:var(--amber)"></i></div>
      </div>`).join('')}
    </div>`;
  }

  function questionsHtml() {
    if (!questions.length) return '';
    return `
<div class="section-title rise rise-5"><span class="i">quiz</span>启动诊断题</div>
<div class="card rise rise-5" style="overflow:hidden">
  ${questions.slice(0, 4).map((q) => `
  <button class="out-item" style="width:100%;text-align:left;border-bottom:1px solid var(--line)" data-practice="${esc(q.id)}">
    <div class="ot-ic qk-blue"><span class="i">edit_note</span></div>
    <div class="ot-tx"><b>${esc(q.stem)}</b><span>${esc(q.solution || '提交自评后更新画像')}</span></div>
    <span class="i">chevron_right</span>
  </button>`).join('')}
</div>`;
  }

  function render() {
    const box = qs('#profile-body', root);
    if (busy) {
      box.innerHTML = `<div class="page-inner">
        <div class="card pad"><div class="skel" style="height:26px;width:45%;margin-bottom:12px"></div><div class="skel" style="height:13px;width:90%"></div></div>
      </div>`;
      return;
    }
    if (!profile) {
      box.innerHTML = `<div class="page-inner"><div class="card"><div class="empty-box">
        <span class="i">neurology</span><h4>画像尚未加载</h4><p>点击右上角刷新。</p>
      </div></div></div>`;
      return;
    }
    const twin = store.activeTwin();
    box.innerHTML = `
<div class="page-inner">
  <div class="card hero-card rise rise-1">
    <div class="hero-top">
      ${twinAvatarHtml(twin, 'hero-avatar')}
      <div class="hero-info">
        <h2>能力画像</h2>
        <div class="status">Level ${profile.level || 1} · XP ${profile.xp || 0} · ${esc(profile.evidence_mode)}</div>
        <div class="status" style="margin-top:3px">已使用 ${profile.attempts_used || 0} 条做题记录 · 同步 ${profile.sync_percent || 0}%</div>
      </div>
    </div>
  </div>
  <div class="section-title rise rise-2"><span class="i">track_changes</span>知识点掌握</div>
  ${masteryHtml(profile.mastery)}
  <div class="section-title rise rise-4"><span class="i">warning</span>薄弱点</div>
  ${masteryHtml(profile.weak_points)}
  <div class="section-title rise rise-5"><span class="i">donut_large</span>错因分布</div>
  ${errorsHtml(profile.error_distribution)}
  ${questionsHtml()}
  <div class="section-title rise rise-5"><span class="i">assistant_direction</span>下一步</div>
  <div class="card evi-list rise rise-5">
    ${(profile.next_actions || []).map((a) => `<div class="evi-item"><span class="i">arrow_right_alt</span><span>${esc(a)}</span></div>`).join('')}
  </div>
  <div style="height:24px"></div>
</div>`;
    root.querySelectorAll('[data-practice]').forEach((btn) => {
      btn.onclick = () => {
        const q = questions.find((item) => item.id === btn.getAttribute('data-practice'));
        window.DSRouter.go('mistakes', { practice: q || null });
      };
    });
  }

  async function load() {
    const twin = store.activeTwin();
    if (!twin || busy) return;
    busy = true; render();
    try {
      const [p, q] = await Promise.all([
        api.getTwinProfile(twin.id),
        api.getQuestions(twin.id, 'diagnostic', 8).catch(() => []),
      ]);
      profile = p;
      questions = q || [];
    } catch (err) { toastError(err); }
    busy = false; render();
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="profile-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">能力画像 <span class="subtitle">BKT · Elo · 错因</span></div>
  <button class="icon-btn primary" id="profile-refresh"><span class="i">refresh</span></button>
</header>
<div class="page-body hide-scrollbar" id="profile-body"></div>`;
    qs('#profile-back', root).addEventListener('click', () => window.DSRouter.back());
    qs('#profile-refresh', root).addEventListener('click', load);
  }

  function show() {
    if (!profile) load();
    else render();
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.profile = { mount, show, invalidate() { profile = null; questions = []; } };
})();
