/* 双生 · 学习路线（路径模拟与筛选交付） */
(function () {
  'use strict';
  const { qs, esc, markSvg, toast, toastError } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let data = null;
  let busy = false;
  let completingTaskId = null;
  let stageTimer = null;

  const STAGES = ['读取分身画像与资料', '整理候选学习路线', '筛选并生成交付清单'];

  function loadingHtml() {
    return `
<div class="card sim-loading rise rise-1">
  <div class="sim-orb">${markSvg()}</div>
  <div class="sim-stage" id="sim-stage">${STAGES[0]}</div>
  <div class="sim-sub">分身正在基于你的真实资料与对话工作</div>
  <div class="sim-track" id="sim-track">${STAGES.map((_, i) => `<i class="${i === 0 ? 'on' : ''}"></i>`).join('')}</div>
</div>`;
  }

  function startStageAnim() {
    let idx = 0;
    stopStageAnim();
    stageTimer = setInterval(() => {
      idx = Math.min(idx + 1, STAGES.length - 1);
      const stage = qs('#sim-stage', root);
      if (stage) stage.textContent = STAGES[idx];
      const track = qs('#sim-track', root);
      if (track) track.querySelectorAll('i').forEach((n, i) => n.classList.toggle('on', i <= idx));
      if (idx >= STAGES.length - 1) stopStageAnim();
    }, 900);
  }
  function stopStageAnim() { if (stageTimer) { clearInterval(stageTimer); stageTimer = null; } }

  function loadChip(value) {
    const map = { '低': 'mint', '中': 'amber', '高': 'coral' };
    return map[value] || 'outline';
  }

  function heroHtml(route) {
    return `
<div class="card route-hero rise rise-1">
  <div class="score-badge"><div><b>${esc(route.score ?? '-')}</b><span>收益分</span></div></div>
  <div class="rh-tag">最终推荐路线</div>
  <h2>${esc(route.name || '推荐路线')}</h2>
  <p>${esc(route.strategy || '')}</p>
  <div class="rh-chips">
    <span class="chip"><span class="i">schedule</span>${esc(route.duration_minutes ?? '-')} 分钟</span>
    <span class="chip"><span class="i">psychology</span>负荷 ${esc(route.cognitive_load || '-')}</span>
    <span class="chip"><span class="i">hourglass_bottom</span>遗忘 ${esc(route.forgetting_risk || '-')}</span>
  </div>
</div>
${route.rationale ? `<div class="card pad rise rise-2" style="margin-top:12px">
  <div style="display:flex;gap:9px">
    <span class="i" style="color:var(--primary);flex-shrink:0;font-size:19px;margin-top:2px">psychology_alt</span>
    <p style="margin:0;font-size:var(--fs-sm);color:var(--ink-2);line-height:1.75">${esc(route.rationale)}</p>
  </div>
</div>` : ''}`;
  }

  function candidatesHtml(routes, recommendedName) {
    if (!routes || routes.length <= 1) return '';
    return `
<div class="section-title rise rise-3"><span class="i">alt_route</span>路径筛选过程</div>
${routes.map((r, i) => {
  const kept = r.name === recommendedName || (i === 0 && !routes.some((x) => x.name === recommendedName));
  return `
<div class="card cand-card ${kept ? '' : 'out'} rise rise-3">
  <div class="cd-head">
    <h4>${esc(r.name)} · ${esc(r.strategy || '')}</h4>
    <span class="chip ${kept ? 'mint' : 'coral'}">${kept ? '保留' : '淘汰'}</span>
  </div>
  <div class="cand-bars">
    <span class="chip blue"><span class="i">military_tech</span>收益 ${esc(r.score ?? '-')}</span>
    <span class="chip"><span class="i">schedule</span>${esc(r.duration_minutes ?? '-')} 分钟</span>
    <span class="chip ${loadChip(r.cognitive_load)}">负荷 ${esc(r.cognitive_load || '-')}</span>
    <span class="chip ${loadChip(r.forgetting_risk)}">遗忘 ${esc(r.forgetting_risk || '-')}</span>
  </div>
  <div class="cand-reason">${kept ? esc(r.rationale || '综合收益最高，进入执行路径。') : `淘汰原因：${esc(r.rationale || '综合评分低于推荐路线。')}`}</div>
</div>`;
}).join('')}`;
  }

  function pathHtml(steps) {
    if (!steps || !steps.length) return '';
    return `
<div class="section-title rise rise-4"><span class="i">footprint</span>执行路径</div>
<div class="timeline rise rise-4">
  ${steps.map((s) => `
  <div class="tl-item">
    <div class="tl-dot">${esc(s.index)}</div>
    <div class="card tl-card">
      <div class="tl-top">
        <span class="chip violet"><span class="i">person</span>${esc(s.teacher || '分身')}</span>
        <span class="chip outline">${esc(s.mode || '')}</span>
      </div>
      <h4>${esc(s.title)}</h4>
      ${s.verification ? `<div class="tl-verify"><span class="i">verified</span><span>验收：${esc(s.verification)}</span></div>` : ''}
    </div>
  </div>`).join('')}
</div>`;
  }

  function evidenceHtml(evidence) {
    if (!evidence || !evidence.length) return '';
    return `
<div class="section-title rise rise-5"><span class="i">fingerprint</span>证据来源</div>
<div class="card evi-list rise rise-5">
  ${evidence.map((e) => `<div class="evi-item"><span class="i">arrow_right_alt</span><span>${esc(e)}</span></div>`).join('')}
</div>`;
  }

  function outputsHtml(outputs) {
    if (!outputs || !outputs.length) return '';
    const iconMap = { '路径': ['route', 'qk-blue'], '黑板': ['cast_for_education', 'qk-violet'], '练习': ['edit_note', 'qk-mint'], '复盘': ['history_edu', 'qk-amber'] };
    return `
<div class="section-title rise rise-5"><span class="i">package_2</span>本次交付</div>
<div class="card rise rise-5" style="overflow:hidden">
  ${outputs.map((o) => {
    const [icon, cls] = iconMap[o.type] || ['inventory_2', 'qk-blue'];
    const done = o.raw_status === 'done';
    const updating = completingTaskId && completingTaskId === o.task_id;
    return `
  <div class="out-item" style="border-bottom:1px solid var(--line)">
    <div class="ot-ic ${cls}"><span class="i">${icon}</span></div>
    <div class="ot-tx"><b>${esc(o.title)}</b><span>${esc(o.detail)}</span></div>
    <span class="chip ${done ? 'mint' : 'blue'}" style="flex-shrink:0">${esc(o.status)}</span>
    ${o.task_id && !done ? `<button class="btn soft sm route-task-done" data-task-id="${esc(o.task_id)}" ${updating ? 'disabled' : ''} style="height:32px;padding:0 12px;flex-shrink:0"><span class="i" style="font-size:15px">${updating ? 'progress_activity' : 'check'}</span>${updating ? '更新中' : '完成'}</button>` : ''}
  </div>`;
  }).join('')}
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px" class="rise rise-5">
  <button class="btn soft" id="route-to-board"><span class="i">cast_for_education</span>去黑板讲解</button>
  <button class="btn ghost" id="route-to-chat"><span class="i">chat</span>和分身讨论</button>
</div>`;
  }

  function normalizePlan(plan) {
    if (!plan || !plan.plan_id) return plan;
    const candidates = plan.candidates || [];
    const chosen = candidates.find((c) => !c.eliminated) || candidates[0] || {};
    const toRisk = (value) => {
      if (value == null) return '-';
      if (value < 0.35) return '低';
      if (value < 0.62) return '中';
      return '高';
    };
    return {
      plan_id: plan.plan_id,
      recommended_route: {
        name: chosen.name || (plan.chosen_route && plan.chosen_route.name) || '推荐路线',
        strategy: chosen.strategy || (plan.chosen_route && plan.chosen_route.strategy) || '',
        score: Math.round((chosen.utility || 0) * 100),
        duration_minutes: chosen.minutes,
        cognitive_load: toRisk(chosen.cognitive_load),
        forgetting_risk: toRisk(chosen.forgetting_risk),
        rationale: chosen.reason || plan.narrative || '',
      },
      routes: candidates.map((c) => ({
        name: c.name,
        strategy: c.strategy,
        score: Math.round((c.utility || 0) * 100),
        duration_minutes: c.minutes,
        cognitive_load: toRisk(c.cognitive_load),
        forgetting_risk: toRisk(c.forgetting_risk),
        rationale: c.reason,
      })),
      optimal_path: (plan.tasks || []).map((task) => ({
        index: task.index,
        title: task.title,
        teacher: task.type === 'practice' ? '训练老师' : task.type === 'blackboard' ? '推导老师' : '规划老师',
        mode: task.type,
        verification: task.completion_criteria,
      })),
      evidence: [
        `画像模式：${plan.profile_summary && plan.profile_summary.mode ? plan.profile_summary.mode : '-'}`,
        `使用做题记录：${plan.profile_summary && plan.profile_summary.attempts_used != null ? plan.profile_summary.attempts_used : 0} 条`,
        plan.narrative || '',
      ].filter(Boolean),
      outputs: (plan.tasks || []).map((task) => ({
        task_id: task.id,
        title: task.title,
        type: task.type === 'blackboard' ? '黑板' : task.type === 'practice' ? '练习' : task.type === 'review' ? '复盘' : '路径',
        detail: `${task.est_minutes} 分钟 · ${task.detail || task.completion_criteria || ''}`,
        status: task.status === 'done' ? '已完成' : task.status === 'doing' ? '进行中' : '待完成',
        raw_status: task.status,
      })),
    };
  }

  function render() {
    const box = qs('#route-body', root);
    if (busy) { box.innerHTML = `<div class="page-inner">${loadingHtml()}</div>`; startStageAnim(); return; }
    if (!data) {
      box.innerHTML = `<div class="page-inner"><div class="card"><div class="empty-box">
        <span class="i">route</span><h4>还没有生成学习路线</h4>
        <p>点击右上角刷新，分身会基于当前资料<br/>重新筛选一条最适合你的路径。</p>
      </div></div></div>`;
      return;
    }
    const route = data.recommended_route || {};
    box.innerHTML = `
<div class="page-inner">
  ${heroHtml(route)}
  ${candidatesHtml(data.routes, route.name)}
  ${pathHtml(data.optimal_path)}
  ${evidenceHtml(data.evidence)}
  ${outputsHtml(data.outputs)}
  <div style="height:24px"></div>
</div>`;
    const toBoard = qs('#route-to-board', root);
    if (toBoard) toBoard.onclick = () => window.DSRouter.go('blackboard');
    const toChat = qs('#route-to-chat', root);
    if (toChat) toChat.onclick = () => window.DSApp.startChatWith(`我想聊聊这条学习路线：${route.name || ''} ${route.strategy || ''}`);
    root.querySelectorAll('.route-task-done').forEach((btn) => {
      btn.addEventListener('click', () => completeTask(btn.getAttribute('data-task-id')));
    });
  }

  async function completeTask(taskId) {
    if (!data || !data.plan_id || !taskId || completingTaskId) return;
    completingTaskId = taskId;
    render();
    try {
      const result = await api.updatePlanTask(data.plan_id, taskId, { status: 'done' });
      data = normalizePlan(result);
      toast('任务已完成', 'ok');
    } catch (err) {
      toastError(err);
    }
    completingTaskId = null;
    render();
  }

  async function load() {
    const twin = store.activeTwin();
    if (!twin || busy) return;
    busy = true; render();
    const begin = Date.now();
    try {
      const result = await api.createPlan(twin.id);
      // 留给分幕动画一点时间，避免闪跳
      const wait = Math.max(0, 1900 - (Date.now() - begin));
      await new Promise((r) => setTimeout(r, wait));
      data = normalizePlan(result);
    } catch (err) { toastError(err); }
    stopStageAnim();
    busy = false; render();
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="route-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">学习路线 <span class="subtitle">分身模拟 · 筛选 · 交付</span></div>
  <button class="icon-btn primary" id="route-refresh"><span class="i">refresh</span></button>
</header>
<div class="page-body hide-scrollbar" id="route-body"></div>`;
    qs('#route-back', root).addEventListener('click', () => window.DSRouter.back());
    qs('#route-refresh', root).addEventListener('click', load);
  }

  function show() {
    if (!data) load();
    else render();
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.route = { mount, show, invalidate() { data = null; } };
})();
