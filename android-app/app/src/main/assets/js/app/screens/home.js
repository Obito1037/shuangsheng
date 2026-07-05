/* 双生 · 主页（分身状态中心） */
(function () {
  'use strict';
  const { qs, esc, markSvg, twinAvatarHtml, fmtDate, toastError } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let todayTwinId = null;
  let profile = null;
  let reviewQueue = [];
  let loadingToday = false;

  function statLine(twin) {
    const s = twin.source_stats || {};
    const materials = (s.notes || 0) + (s.courseware || 0) + (s.assignments || 0);
    return [
      { n: materials, label: '学习资料', cls: 'c-blue', to: 'library' },
      { n: s.mistakes || 0, label: '错题资料', cls: 'c-amber', to: 'mistakes' },
      { n: s.conversations || 0, label: '对话训练', cls: 'c-mint', to: null },
      { n: s.audio || 0, label: '口语语音', cls: 'c-violet', to: 'library' },
    ];
  }

  function heroHtml(twin) {
    const pct = Math.max(0, Math.min(100, twin.sync_percent || 0));
    return `
<div class="card hero-card rise rise-1">
  <div class="hero-top">
    <div class="hero-avatar-wrap">
      ${twinAvatarHtml(twin, 'hero-avatar')}
    </div>
    <div class="hero-info">
      <h2>${esc(twin.name)}</h2>
      <div class="status">同步进度 <span class="pct">${pct}%</span> · ${esc(twin.stage || '')}</div>
      <div class="status" style="margin-top:3px">${esc(twin.status || '')}</div>
    </div>
  </div>
  <div class="hero-chips">
    <span class="chip blue"><span class="i">category</span>${esc(twin.subject || '综合学习')}</span>
    <button class="chip outline clickable" data-nav="settings"><span class="i">tune</span>管理分身</button>
    <button class="chip outline clickable" id="btn-sync-twin"><span class="i">sync</span>立即同步</button>
  </div>
  ${twin.goal ? `<div class="hero-goal"><span class="i">flag</span><span>${esc(twin.goal)}</span></div>` : ''}
</div>`;
  }

  function quickHtml() {
    const items = [
      ['library', 'qk-blue', 'cloud_upload', '训练资料', '上传并喂给分身'],
      ['memory', 'qk-mint', 'hub', '记忆可视化', 'RAG 向量与图谱'],
      ['profile', 'qk-violet', 'analytics', '能力画像', '查看掌握与错因'],
      ['route', 'qk-mint', 'route', '学习路线', '分身筛选最优路径'],
      ['blackboard', 'qk-blue', 'cast_for_education', '黑板讲解', '分步推导讲给你听'],
      ['mistakes', 'qk-amber', 'fact_check', '错题薄弱', '定位并复盘弱点'],
    ];
    return `
<div class="quick-grid rise rise-3">
  ${items.map(([to, cls, icon, title, sub]) => `
  <button class="card quick-card tappable" data-nav="${to}">
    <div class="qk-icon ${cls}"><span class="i">${icon}</span></div>
    <b>${title}</b><span>${sub}</span>
  </button>`).join('')}
</div>`;
  }

  function workHtml(twin) {
    const steps = twin.current_work || [];
    if (!steps.length) return '';
    const iconOf = { done: 'check', active: 'progress_activity', pending: 'more_horiz' };
    return `
<div class="section-title rise rise-4"><span class="i">smart_toy</span>分身正在做</div>
<div class="card work-steps rise rise-4">
  ${steps.map((w) => `
  <div class="work-step ${esc(w.state)}">
    <div class="work-dot"><span class="i" style="font-size:14px">${iconOf[w.state] || 'circle'}</span></div>
    <div><div class="wtitle">${esc(w.title)}</div><div class="wdetail">${esc(w.detail)}</div></div>
  </div>`).join('')}
</div>`;
  }

  function todayHtml() {
    if (loadingToday && !profile) {
      return `<div class="section-title rise rise-4"><span class="i">today</span>今日三件事</div>
      <div class="card pad rise rise-4"><div class="skel" style="height:16px;width:70%;margin-bottom:10px"></div><div class="skel" style="height:13px;width:90%"></div></div>`;
    }
    const items = [];
    const due = reviewQueue.length;
    items.push({
      icon: 'event_repeat',
      cls: due ? 'qk-amber' : 'qk-mint',
      title: due ? `${due} 个复习项到期` : '暂无到期复习',
      detail: due ? (reviewQueue[0].action || reviewQueue[0].detail || '先处理优先级最高的一项') : '保持节奏，适合做一题探边',
      to: 'review',
    });
    const weak = profile && profile.weak_points && profile.weak_points[0];
    items.push({
      icon: 'track_changes',
      cls: weak ? 'qk-amber' : 'qk-blue',
      title: weak ? `薄弱点：${weak.name}` : '画像仍在启动',
      detail: weak ? `掌握 ${Math.round((weak.p_mastery || 0) * 100)}%，建议做 1 道诊断题` : '先完成诊断题，让分身有真实数据',
      to: 'profile',
    });
    const attempts = profile ? (profile.attempts_used || 0) : 0;
    items.push({
      icon: attempts < 10 ? 'quiz' : 'route',
      cls: attempts < 10 ? 'qk-violet' : 'qk-mint',
      title: attempts < 10 ? '诊断先行' : '可以模拟路线',
      detail: attempts < 10 ? `已有 ${attempts}/10 条做题证据，先补足诊断` : '画像证据足够，进入路径筛选',
      to: attempts < 10 ? 'mistakes' : 'route',
    });
    return `
<div class="section-title rise rise-4"><span class="i">today</span>今日三件事</div>
<div class="card rise rise-4" style="overflow:hidden">
  ${items.map((item) => `
  <button class="out-item" data-nav="${item.to}" style="width:100%;text-align:left;border-bottom:1px solid var(--line)">
    <div class="ot-ic ${item.cls}"><span class="i">${item.icon}</span></div>
    <div class="ot-tx"><b>${esc(item.title)}</b><span>${esc(item.detail)}</span></div>
    <span class="i">chevron_right</span>
  </button>`).join('')}
</div>`;
  }

  function convsHtml() {
    const convs = store.state.conversations.slice(0, 3);
    if (!convs.length) {
      return `
<div class="section-title rise rise-5"><span class="i">forum</span>最近对话</div>
<div class="card rise rise-5"><div class="empty-box" style="padding:26px">
  <span class="i">chat_bubble</span><h4>还没有对话</h4><p>在下方输入框提出第一个问题，<br/>分身会把它记进自己的记忆。</p>
</div></div>`;
    }
    return `
<div class="section-title rise rise-5"><span class="i">forum</span>最近对话
  <span class="spacer"></span><button class="link" id="btn-all-convs">全部</button>
</div>
<div class="card rise rise-5" style="overflow:hidden">
  ${convs.map((c) => `
  <button class="conv-row app-conv" data-conv="${esc(c.id)}" style="width:100%;text-align:left;border-bottom:1px solid var(--line)">
    <div class="cv-ic"><span class="i">chat_bubble</span></div>
    <div class="cv-tx"><b>${esc(c.title)}</b><span>${fmtDate(c.updated_at)}</span></div>
    <span class="i">chevron_right</span>
  </button>`).join('')}
</div>`;
  }

  function onboardHtml() {
    return `
<div class="onboard">
  <div class="ob-avatar">${markSvg()}</div>
  <h2>创建你的学习分身</h2>
  <p>分身会持续吸收你的资料、错题和对话，<br/>替你模拟学习路径、筛选训练方案。</p>
  <div class="onboard-steps">
    <div class="os rise rise-1"><div class="n">1</div><span>填写学习方向与目标，生成专属分身</span></div>
    <div class="os rise rise-2"><div class="n">2</div><span>上传资料、错题或直接对话来训练它</span></div>
    <div class="os rise rise-3"><div class="n">3</div><span>让分身模拟多条路径，交付最优方案</span></div>
  </div>
  <button class="btn primary block" data-nav="twin-new" style="max-width:340px;margin:0 auto">
    <span class="i">add_circle</span>立即创建
  </button>
</div>`;
  }

  function composerHtml(hasTwin) {
    return `
<div class="composer-zone" style="position:absolute">
  <div class="composer" style="pointer-events:auto">
    <button class="icon-btn" id="home-upload-btn"><span class="i">add</span></button>
    <textarea id="home-input" rows="1" placeholder="${hasTwin ? '向分身提问，或说出今天的学习目标…' : '先创建学习分身，再开始训练…'}" ${hasTwin ? '' : 'disabled'}></textarea>
    <button class="send" id="home-send"><span class="i fill" style="font-size:20px">arrow_upward</span></button>
  </div>
</div>`;
  }

  function render() {
    if (!root) return;
    const twin = store.activeTwin();
    const body = qs('#home-body', root);
    if (!twin) {
      qs('#home-title', root).innerHTML = '双生 <span class="subtitle">你的学习分身工作台</span>';
      body.innerHTML = `<div class="page-inner">${onboardHtml()}</div>`;
      qs('#home-composer-slot', root).innerHTML = '';
      bindNav();
      return;
    }
    qs('#home-title', root).innerHTML = `${esc(twin.name)} <span class="subtitle">${esc(twin.subject || '')} · 同步 ${twin.sync_percent || 0}%</span>`;
    const stats = statLine(twin);
    body.innerHTML = `
<div class="page-inner">
  ${heroHtml(twin)}
  <div class="stat-row rise rise-2">
    ${stats.map((s) => `
    <button class="stat-cell ${s.cls}" ${s.to ? `data-nav="${s.to}"` : ''}>
      <b>${s.n}</b><span>${s.label}</span>
    </button>`).join('')}
  </div>
  <div class="section-title rise rise-3"><span class="i">bolt</span>分身能力</div>
  ${quickHtml()}
  ${todayHtml()}
  ${workHtml(twin)}
  ${convsHtml()}
  <div style="height:110px"></div>
</div>`;
    qs('#home-composer-slot', root).innerHTML = composerHtml(true);
    bindNav();
    bindComposer();
    const syncBtn = qs('#btn-sync-twin', root);
    if (syncBtn) syncBtn.addEventListener('click', async () => {
      syncBtn.style.opacity = '0.5';
      try {
        await api.syncTwin(twin.id);
        await window.DSApp.refreshTwins();
        window.DSUi.toast('分身已重新同步', 'ok');
      } catch (err) { toastError(err); }
      syncBtn.style.opacity = '';
    });
  }

  async function loadToday(force) {
    const twin = store.activeTwin();
    if (!twin) { profile = null; reviewQueue = []; todayTwinId = null; return; }
    if (!force && todayTwinId === twin.id && profile) return;
    todayTwinId = twin.id;
    loadingToday = true;
    render();
    try {
      const [p, rq] = await Promise.all([
        api.getTwinProfile(twin.id).catch(() => null),
        api.getReviewQueue(twin.id, 6).catch(() => []),
      ]);
      profile = p;
      reviewQueue = rq || [];
    } catch (err) { toastError(err); }
    loadingToday = false;
    render();
  }

  function bindNav() {
    root.querySelectorAll('[data-nav]').forEach((n) => {
      n.onclick = () => window.DSRouter.go(n.getAttribute('data-nav'));
    });
    root.querySelectorAll('[data-conv]').forEach((n) => {
      n.onclick = () => window.DSApp.openConversation(n.getAttribute('data-conv'));
    });
    const all = qs('#btn-all-convs', root);
    if (all) all.onclick = () => window.DSApp.openDrawer();
  }

  function bindComposer() {
    const input = qs('#home-input', root);
    const send = qs('#home-send', root);
    if (!input) return;
    const submit = () => {
      const text = input.value.trim();
      if (!text) { window.DSRouter.go('chat'); return; }
      input.value = '';
      window.DSApp.startChatWith(text);
    };
    send.onclick = submit;
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    const uploadBtn = qs('#home-upload-btn', root);
    if (uploadBtn) uploadBtn.onclick = () => window.DSRouter.go('library');
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="home-menu"><span class="i">menu</span></button>
  <div class="title" id="home-title">双生</div>
  <button class="icon-btn" data-nav-static="settings"><span class="i">settings</span></button>
</header>
<div class="page-body hide-scrollbar" id="home-body"></div>
<div id="home-composer-slot"></div>`;
    qs('#home-menu', root).addEventListener('click', () => window.DSApp.openDrawer());
    root.querySelector('[data-nav-static]').addEventListener('click', () => window.DSRouter.go('settings'));
  }

  function show() {
    render();
    loadToday(false);
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.home = { mount, show, render, invalidate() { profile = null; reviewQueue = []; todayTwinId = null; } };
})();
