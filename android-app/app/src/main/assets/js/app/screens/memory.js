/* 双生 · 记忆可视化（RAG 文本向量 2D 投影 + 知识点图谱） */
(function () {
  'use strict';
  const { qs, esc, toast, toastError } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let data = null;
  let busy = false;

  const DOC_COLORS = ['#0EA5F0', '#0FA97D', '#7C6CF0', '#E8930C', '#E25563', '#12B5B0'];

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888';
  }

  function summaryHtml(s) {
    return `
<div class="stat-row rise rise-1" style="grid-template-columns:repeat(4,1fr)">
  <div class="stat-cell c-blue"><b>${s.chunks}</b><span>记忆分块</span></div>
  <div class="stat-cell c-mint"><b>${s.embedded}</b><span>已向量化</span></div>
  <div class="stat-cell c-violet"><b>${s.knowledge_points}</b><span>知识点</span></div>
  <div class="stat-cell c-amber"><b>${s.dim || '—'}</b><span>向量维度</span></div>
</div>`;
  }

  function legendHtml(docs) {
    if (!docs.length) return '';
    return `<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:12px">
      ${docs.map((d) => `<div style="display:flex;align-items:center;gap:6px;font-size:var(--fs-xs);color:var(--ink-2)">
        <span style="width:10px;height:10px;border-radius:3px;background:${DOC_COLORS[d.index % DOC_COLORS.length]}"></span>
        ${esc(d.title)} · ${d.chunks}
      </div>`).join('')}
    </div>`;
  }

  function render() {
    const box = qs('#mem-body', root);
    if (busy) {
      box.innerHTML = `<div class="page-inner">
        <div class="card sim-loading"><div class="sim-orb">${window.DSUi.markSvg()}</div>
        <div class="sim-stage">正在读取分身记忆…</div>
        <div class="sim-sub">加载文本向量与知识点图谱</div></div>
      </div>`;
      return;
    }
    if (!data) {
      box.innerHTML = `<div class="page-inner"><div class="card"><div class="empty-box">
        <span class="i">hub</span><h4>还没有可视化的记忆</h4>
        <p>上传并解析资料后，这里会显示分身的<br/>文本向量分布和知识点图谱。</p>
      </div></div></div>`;
      return;
    }
    const s = data.summary;
    const pending = s.projection === 'pending';
    box.innerHTML = `
<div class="page-inner">
  ${summaryHtml(s)}

  <div class="section-title rise rise-2"><span class="i">scatter_plot</span>RAG 文本向量分布
    <span class="spacer"></span><span class="chip ${pending ? 'amber' : 'mint'}">${pending ? 'PCA 待云端向量' : 'PCA 降维'}</span>
  </div>
  <div class="card pad rise rise-2">
    <p style="margin:0 0 12px;font-size:var(--fs-xs);color:var(--ink-3);line-height:1.6">
      每个点是一段被切分并${pending ? '待' : '已'}向量化的资料。语义相近的分块在 768 维空间中距离更近，
      降到平面后会自然聚成簇——这正是分身检索（RAG）时"找相关内容"的依据。
    </p>
    <canvas id="mem-vec-canvas" style="width:100%;height:280px;display:block"></canvas>
    ${legendHtml(data.documents)}
    ${pending ? '<p style="margin:12px 0 0;font-size:var(--fs-xs);color:var(--amber)">当前分块尚未在云端完成 embedding，点位为占位布局；连上带密钥的云端后会显示真实向量投影。</p>' : ''}
  </div>

  <div class="section-title rise rise-3"><span class="i">account_tree</span>知识点图谱
    <span class="spacer"></span><span class="chip blue">${data.knowledge_points.length} 点 · ${data.edges.length} 关系</span>
  </div>
  <div class="card pad rise rise-3">
    <p style="margin:0 0 12px;font-size:var(--fs-xs);color:var(--ink-3);line-height:1.6">
      节点大小代表掌握度（BKT 概率），越大越牢固；连线是先修关系。红色节点是分身识别出的薄弱环节。
    </p>
    <canvas id="mem-kp-canvas" style="width:100%;height:300px;display:block"></canvas>
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:12px">
      <div style="display:flex;align-items:center;gap:6px;font-size:var(--fs-xs);color:var(--ink-2)"><span style="width:10px;height:10px;border-radius:50%;background:var(--coral)"></span>薄弱 (&lt;60%)</div>
      <div style="display:flex;align-items:center;gap:6px;font-size:var(--fs-xs);color:var(--ink-2)"><span style="width:10px;height:10px;border-radius:50%;background:var(--amber)"></span>巩固中</div>
      <div style="display:flex;align-items:center;gap:6px;font-size:var(--fs-xs);color:var(--ink-2)"><span style="width:10px;height:10px;border-radius:50%;background:var(--mint)"></span>已掌握 (&gt;75%)</div>
    </div>
  </div>
  <div style="height:24px"></div>
</div>`;

    requestAnimationFrame(() => {
      drawVectors(qs('#mem-vec-canvas', root), data.vectors);
      drawGraph(qs('#mem-kp-canvas', root), data.knowledge_points, data.edges);
    });
  }

  function setupCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || 320;
    const h = parseInt(canvas.style.height, 10) || 280;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    return { ctx, w, h };
  }

  function drawVectors(canvas, vectors) {
    if (!canvas || !vectors.length) return;
    const { ctx, w, h } = setupCanvas(canvas);
    const pad = 22;
    const toPx = (x, y) => [pad + ((x + 1) / 2) * (w - 2 * pad), pad + ((y + 1) / 2) * (h - 2 * pad)];
    // 背景网格
    ctx.strokeStyle = cssVar('--line');
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i += 1) {
      const gx = pad + (i / 4) * (w - 2 * pad);
      const gy = pad + (i / 4) * (h - 2 * pad);
      ctx.beginPath(); ctx.moveTo(gx, pad); ctx.lineTo(gx, h - pad); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(w - pad, gy); ctx.stroke();
    }
    vectors.forEach((v) => {
      const [px, py] = toPx(v.x, v.y);
      const color = DOC_COLORS[v.doc_index % DOC_COLORS.length];
      ctx.beginPath();
      ctx.arc(px, py, v.embedded ? 6 : 4.5, 0, Math.PI * 2);
      ctx.fillStyle = v.embedded ? color : 'transparent';
      ctx.globalAlpha = v.embedded ? 0.82 : 1;
      ctx.fill();
      if (!v.embedded) { ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.setLineDash([2, 2]); ctx.stroke(); ctx.setLineDash([]); }
      ctx.globalAlpha = 1;
    });
  }

  function drawGraph(canvas, nodes, edges) {
    if (!canvas || !nodes.length) return;
    const { ctx, w, h } = setupCanvas(canvas);
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) / 2 - 46;
    // 环形布局：按掌握度排序，薄弱点靠上
    const sorted = [...nodes].sort((a, b) => a.p_mastery - b.p_mastery);
    const pos = {};
    sorted.forEach((n, i) => {
      const angle = -Math.PI / 2 + (i / sorted.length) * Math.PI * 2;
      pos[n.id] = [cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius];
    });
    // 边
    ctx.strokeStyle = cssVar('--primary');
    ctx.globalAlpha = 0.28;
    ctx.lineWidth = 1.5;
    edges.forEach((e) => {
      const a = pos[e.source]; const b = pos[e.target];
      if (!a || !b) return;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    });
    ctx.globalAlpha = 1;
    // 节点
    const colorMint = cssVar('--mint'); const colorAmber = cssVar('--amber'); const colorCoral = cssVar('--coral');
    nodes.forEach((n) => {
      const p = pos[n.id];
      const r = 9 + n.p_mastery * 16;
      const color = n.p_mastery >= 0.75 ? colorMint : (n.p_mastery >= 0.6 ? colorAmber : colorCoral);
      ctx.beginPath(); ctx.arc(p[0], p[1], r, 0, Math.PI * 2);
      ctx.fillStyle = color; ctx.globalAlpha = 0.9; ctx.fill(); ctx.globalAlpha = 1;
      ctx.fillStyle = cssVar('--ink');
      ctx.font = '11px "Plus Jakarta Sans", sans-serif';
      ctx.textAlign = 'center';
      const label = n.name.length > 7 ? `${n.name.slice(0, 7)}…` : n.name;
      const ly = p[1] + (p[1] < cy ? -r - 6 : r + 14);
      ctx.fillText(label, p[0], ly);
    });
  }

  async function load(force) {
    const twin = store.activeTwin();
    if (!twin || (busy && !force)) return;
    busy = true; render();
    try {
      data = await api.getMemoryMap(twin.id);
    } catch (err) { toastError(err); }
    busy = false; render();
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="mem-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">记忆可视化 <span class="subtitle">RAG 向量 · 知识图谱</span></div>
  <button class="icon-btn primary" id="mem-refresh"><span class="i">refresh</span></button>
</header>
<div class="page-body hide-scrollbar" id="mem-body"></div>`;
    qs('#mem-back', root).addEventListener('click', () => window.DSRouter.back());
    qs('#mem-refresh', root).addEventListener('click', () => load(true));
  }

  function show() {
    if (!data) load();
    else render();
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.memory = { mount, show, invalidate() { data = null; } };
})();
