(function () {
  const TOKEN_KEY = 'dualsheng.tokens';
  const isAppAssets = location.hostname === 'appassets.androidplatform.net';

  function readTokens() {
    try { return JSON.parse(localStorage.getItem(TOKEN_KEY) || 'null'); } catch (_) { return null; }
  }

  const client = {
    baseUrl: isAppAssets ? 'http://8.148.69.255' : 'http://127.0.0.1:8000',
    tokens: readTokens(),
    setTokens(tokens) {
      this.tokens = tokens || null;
      if (this.tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(this.tokens));
      else localStorage.removeItem(TOKEN_KEY);
    },
    async request(path, options = {}) {
      const headers = new Headers(options.headers || {});
      if (this.tokens?.access_token) headers.set('Authorization', `Bearer ${this.tokens.access_token}`);
      if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
      let response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
      if (response.status === 401 && this.tokens?.refresh_token && !options.skipRefresh) {
        const refreshed = await this.refreshToken().catch(() => null);
        if (refreshed?.access_token) {
          headers.set('Authorization', `Bearer ${refreshed.access_token}`);
          response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
        }
      }
      const text = await response.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch (_) { data = { message: text.slice(0, 240) || `HTTP ${response.status}` }; }
      if (!response.ok) {
        const message = data?.message || data?.detail || `HTTP ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        error.payload = data;
        throw error;
      }
      return data;
    },
    login(account, password) { return this.request('/api/auth/login', { method: 'POST', body: JSON.stringify({ login_type: 'password', account, password, device: { platform: 'android-webview' } }) }); },
    async testLogin() { const res = await this.request('/api/auth/test-login', { method: 'POST' }); this.setTokens(res.tokens); return res; },
    loginWithEmailCode(email, code) { return this.request('/api/auth/email/login', { method: 'POST', body: JSON.stringify({ email, code }) }); },
    sendEmailCode(email, purpose = 'register') { return this.request('/api/auth/email/send-code', { method: 'POST', body: JSON.stringify({ email, purpose }) }); },
    verifyEmailCode(email, code, purpose = 'register') { return this.request('/api/auth/email/verify-code', { method: 'POST', body: JSON.stringify({ email, purpose, code }) }); },
    register(email, password, displayName, emailCode, verifiedToken) { return this.request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, display_name: displayName || null, email_code: emailCode || null, verified_token: verifiedToken || null }) }); },
    async refreshToken() {
      if (!this.tokens?.refresh_token) throw new Error('No refresh token');
      const refreshed = await this.request('/api/auth/refresh', { method: 'POST', skipRefresh: true, body: JSON.stringify({ refresh_token: this.tokens.refresh_token }) });
      this.setTokens({ ...this.tokens, ...refreshed });
      return refreshed;
    },
    getMe() { return this.request('/api/users/me'); },
    getUsage() { return this.request('/api/usage/me'); },
    listTwins() { return this.request('/api/twins'); },
    createTwin(payload) { return this.request('/api/twins', { method: 'POST', body: JSON.stringify(payload) }); },
    listConversations(twinId) { return this.request(`/api/conversations${twinId ? `?twin_id=${encodeURIComponent(twinId)}` : ''}`); },
    createConversation(title, twinId) { return this.request('/api/conversations', { method: 'POST', body: JSON.stringify({ title: title || '新对话', twin_id: twinId || null }) }); },
    getConversation(id) { return this.request(`/api/conversations/${id}`); },
    sendMessage(payload) { return this.request('/api/chat/message', { method: 'POST', body: JSON.stringify(payload) }); },
    uploadFile(file) { const form = new FormData(); form.append('upload', file); return this.request('/api/files/upload', { method: 'POST', body: form }); },
    listFiles() { return this.request('/api/files'); },
    listDocuments(twinId) { return this.request(`/api/documents${twinId ? `?twin_id=${encodeURIComponent(twinId)}` : ''}`); },
    parseDocument(fileId, twinId) { return this.request('/api/documents/parse', { method: 'POST', body: JSON.stringify({ file_id: fileId, twin_id: twinId || null }) }); },
    simulateTwin(id) { return this.request(`/api/twins/${id}/simulate`, { method: 'POST', body: '{}' }); },
    getWeakPoints(id) { return this.request(`/api/twins/${id}/weak-points`); },
    getBlackboard(id, topic) { return this.request(`/api/twins/${id}/blackboard`, { method: 'POST', body: JSON.stringify({ topic: topic || null }) }); },
  };
  window.DualShengApiClient = client;
})();

(function () {
  function ready(fn) { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn(); }
  function escapeHtml(value) { return String(value || '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char])); }
  function selectedTwinId() { return window.app?.state?.selectedTwinId || null; }
  function showNotice(message) { if (window.alert) window.alert(message); else console.warn(message); }

  function ensureMathRenderer() {
    if (window.MathJax?.typesetPromise || document.getElementById('dualsheng-mathjax')) return;
    window.MathJax = { tex: { inlineMath: [['$', '$'], ['\\(', '\\)']], displayMath: [['$$', '$$'], ['\\[', '\\]']], processEscapes: true }, svg: { fontCache: 'global' } };
    const script = document.createElement('script');
    script.id = 'dualsheng-mathjax';
    script.async = true;
    script.src = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js';
    document.head.appendChild(script);
  }

  function typesetMath(root) {
    ensureMathRenderer();
    const attempt = () => window.MathJax?.typesetPromise?.([root]).catch(() => null);
    setTimeout(attempt, 80);
    setTimeout(attempt, 500);
  }

  function formulaBlock(value) {
    const formula = String(value || '').trim();
    if (!formula) return '';
    const hasLatex = /\\|\^|_|\{|\}|\$|=|\+|-|\\frac|\\sum|\\int|\\lim/.test(formula);
    const body = hasLatex ? `\\[${escapeHtml(formula)}\\]` : escapeHtml(formula);
    return `<div class="bg-black/20 rounded-xl px-3 py-2 my-2 overflow-x-auto text-white/95 text-base leading-relaxed math-block">${body}</div>`;
  }

  function routeCard(route, index, recommendedName) {
    const kept = index === 0 || route.name === recommendedName;
    const box = kept ? 'border-brand-blue/20 bg-white' : 'border-error/10 bg-white opacity-60';
    const title = kept ? '' : 'line-through decoration-error decoration-2';
    const tag = kept ? '保留' : '淘汰';
    const tagStyle = kept ? 'bg-brand-light-blue text-brand-blue' : 'bg-error/10 text-error';
    const reason = kept ? '综合收益最高，进入执行路径。' : `淘汰原因：收益 ${escapeHtml(route.score ?? '-')}，负荷 ${escapeHtml(route.cognitive_load || '-')}，遗忘风险 ${escapeHtml(route.forgetting_risk || '-')}。`;
    return `<div class="app-card p-4 border ${box}"><div class="flex items-start justify-between gap-3 mb-2"><h3 class="font-semibold text-on-surface ${title}">${escapeHtml(route.name || `路线${index + 1}`)} · ${escapeHtml(route.strategy || '')}</h3><span class="text-xs px-2 py-1 rounded-full shrink-0 ${tagStyle}">${tag}</span></div><div class="flex flex-wrap gap-2 text-xs text-on-surface-variant mb-2"><span class="px-2 py-1 rounded-full bg-brand-surface">收益 ${escapeHtml(route.score ?? '-')}</span><span class="px-2 py-1 rounded-full bg-brand-surface">${escapeHtml(route.duration_minutes ?? '-')} 分钟</span><span class="px-2 py-1 rounded-full bg-brand-surface">负荷 ${escapeHtml(route.cognitive_load || '-')}</span><span class="px-2 py-1 rounded-full bg-brand-surface">遗忘 ${escapeHtml(route.forgetting_risk || '-')}</span></div><p class="text-xs text-on-surface-variant leading-relaxed">${reason}</p></div>`;
  }

  function renderRouteLoading() {
    const root = document.querySelector('#screen-learning-route main .max-w-[600px]');
    if (root) root.innerHTML = '<div class="app-card p-5 text-center text-sm text-on-surface-variant">正在训练分身、读取缓存资料并筛选学习路径...</div>';
  }

  function renderRoute(data) {
    const root = document.querySelector('#screen-learning-route main .max-w-[600px]');
    if (!root || !data) return;
    const route = data.recommended_route || {};
    const routes = data.routes || [];
    const steps = data.optimal_path || [];
    const evidence = data.evidence || [];
    const outputs = data.outputs || [];
    root.innerHTML = `<div class="app-card p-5 mb-4 border border-brand-blue/10"><div class="text-xs text-brand-blue font-semibold mb-2">最终推荐路线</div><h2 class="text-lg font-bold text-on-surface mb-2">${escapeHtml(route.name || '路线 A')} · ${escapeHtml(route.strategy || '生成学习路径')}</h2><p class="text-sm text-on-surface-variant leading-relaxed">${escapeHtml(route.rationale || '基于当前分身资料和学习行为生成。')}</p></div><div class="mb-4"><h3 class="font-semibold text-on-surface mb-3">路径筛选过程</h3><div class="space-y-3">${(routes.length ? routes : [route]).map((item, index) => routeCard(item, index, route.name)).join('')}</div></div><div class="relative border-l-2 border-brand-blue/20 ml-2 space-y-4 pb-6 mb-4">${steps.map((step) => `<div class="relative pl-6"><div class="absolute -left-[11px] top-1 w-5 h-5 rounded-full bg-brand-blue border-4 border-brand-main-bg shadow-sm"></div><div class="app-card p-4"><div class="text-xs text-brand-blue font-semibold mb-1">第 ${escapeHtml(step.index)} 步 · ${escapeHtml(step.teacher)}</div><h3 class="font-semibold text-on-surface mb-1">${escapeHtml(step.title)}</h3><p class="text-sm text-on-surface-variant mb-2">模式：${escapeHtml(step.mode)}</p><p class="text-xs text-on-surface-variant">验收：${escapeHtml(step.verification)}</p></div></div>`).join('')}</div><div class="app-card p-4 mb-4"><h3 class="font-semibold text-on-surface mb-3">证据来源</h3><div class="space-y-2">${evidence.map((item) => `<div class="text-sm text-on-surface-variant">• ${escapeHtml(item)}</div>`).join('') || '<div class="text-sm text-on-surface-variant">暂无足够证据，先上传资料或开始对话。</div>'}</div></div><div class="app-card p-4 mb-safe-bottom"><h3 class="font-semibold text-on-surface mb-3">本次交付</h3><div class="space-y-3">${outputs.map((item) => `<div class="p-3 rounded-2xl bg-brand-surface/70"><div class="flex justify-between gap-3 mb-1"><span class="font-medium text-sm text-on-surface">${escapeHtml(item.title)}</span><span class="text-xs text-brand-blue shrink-0">${escapeHtml(item.status)}</span></div><div class="text-xs text-on-surface-variant">${escapeHtml(item.type)} · ${escapeHtml(item.detail)}</div></div>`).join('') || '<div class="text-sm text-on-surface-variant">暂无交付内容。</div>'}</div></div>`;
  }

  function renderBlackboardLoading() {
    const root = document.querySelector('#screen-blackboard main .max-w-[800px]');
    if (root) root.innerHTML = '<div class="text-white/70 text-center">正在生成黑板讲解...</div>';
  }

  function renderBlackboard(data) {
    const title = document.querySelector('#screen-blackboard header h1');
    if (title) title.textContent = data?.topic || '黑板讲解';
    const root = document.querySelector('#screen-blackboard main .max-w-[800px]');
    if (!root || !data) return;
    const steps = data.steps || [];
    root.innerHTML = `<div class="bg-[#2A3036] rounded-[24px] border border-white/5 shadow-2xl p-5 md:p-8 w-full"><div class="text-white/60 text-sm mb-4">${escapeHtml(data.topic || '黑板讲解')}</div><div class="space-y-4">${steps.map((step) => `<div class="rounded-2xl bg-white/5 p-4 border border-white/5"><div class="text-brand-blue text-sm font-semibold mb-1">步骤 ${escapeHtml(step.index)} · ${escapeHtml(step.title)}</div>${formulaBlock(step.formula)}<p class="text-white/70 text-sm leading-relaxed whitespace-pre-wrap">${escapeHtml(step.explanation)}</p>${step.check_question ? `<p class="text-white/50 text-xs mt-2">自检：${escapeHtml(step.check_question)}</p>` : ''}</div>`).join('')}</div></div>`;
    typesetMath(root);
  }

  async function refreshLearning(screenId) {
    const api = window.DualShengApiClient;
    const twinId = selectedTwinId();
    if (!api || !api.tokens?.access_token || !twinId) return;
    try {
      if (screenId === 'learning-route') { renderRouteLoading(); renderRoute(await api.simulateTwin(twinId)); }
      if (screenId === 'blackboard') { renderBlackboardLoading(); renderBlackboard(await api.getBlackboard(twinId, null)); }
    } catch (error) { showNotice(error?.message || '生成学习路径失败，请稍后再试。'); }
  }

  function install() {
    const api = window.DualShengApiClient;
    if (!api || !window.app || api.__learningRendererInstalledV4) return false;
    api.__learningRendererInstalledV4 = true;
    const rawSend = api.sendMessage.bind(api);
    api.sendMessage = function (payload) { return rawSend({ ...payload, twin_id: payload?.twin_id || window.app?.state?.selectedTwinId || null, mode: payload?.mode || window.app?.state?.aiMode || 'twin' }); };
    const rawNavigate = window.app.navigate.bind(window.app);
    window.app.navigate = function (screenId) { const result = rawNavigate(screenId); if (screenId === 'learning-route' || screenId === 'blackboard') setTimeout(() => refreshLearning(screenId), 0); return result; };
    return true;
  }
  ready(() => { let tries = 0; const timer = setInterval(() => { tries += 1; if (install() || tries > 30) clearInterval(timer); }, 100); });
})();
