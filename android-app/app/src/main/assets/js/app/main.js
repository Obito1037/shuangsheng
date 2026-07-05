/* 双生 · 应用主控（路由 / 抽屉 / 数据编排 / Android 桥） */
(function () {
  'use strict';
  const { qs, qsa, esc, toast, toastError, setScrim, logoSvg, twinAvatarHtml, userAvatarHtml, fmtDate, closeDoc } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  /* ================= 路由 ================= */
  const SCREENS = ['auth', 'home', 'chat', 'twin-new', 'library', 'route', 'profile', 'review', 'blackboard', 'mistakes', 'settings'];
  const TWIN_REQUIRED = new Set(['library', 'route', 'profile', 'review', 'blackboard', 'mistakes']);
  let stack = ['home'];

  const router = {
    current() { return stack[stack.length - 1]; },
    go(screenId, params) {
      if (!SCREENS.includes(screenId)) { toast('该页面暂未开放', 'info'); return; }
      if (TWIN_REQUIRED.has(screenId) && !store.activeTwin()) {
        toast('先创建一个学习分身吧', 'info');
        screenId = 'twin-new';
      }
      if (this.current() === screenId) { activate(screenId, params); return; }
      stack.push(screenId);
      if (stack.length > 12) stack = stack.slice(-12);
      activate(screenId, params);
    },
    back() {
      if (stack.length <= 1) return false;
      stack.pop();
      activate(this.current());
      return true;
    },
    resetTo(screenId) {
      stack = [screenId];
      activate(screenId);
    },
  };

  function activate(screenId, params) {
    closeDrawer();
    store.set({ screen: screenId });
    qsa('.screen').forEach((node) => {
      const on = node.id === `screen-${screenId}`;
      if (on) { node.classList.remove('leaving'); node.classList.add('active'); }
      else if (node.classList.contains('active')) {
        node.classList.add('leaving'); node.classList.remove('active');
        setTimeout(() => node.classList.remove('leaving'), 300);
      }
    });
    const screen = window.DSScreens[screenId];
    if (screen && screen.show) { try { screen.show(params); } catch (err) { console.error(err); } }
  }

  /* ================= 抽屉 ================= */
  function drawerHtml() {
    const twins = store.state.twins;
    const activeId = store.state.activeTwinId;
    const user = store.state.user;
    let listHtml;
    if (!twins.length) {
      listHtml = `<div class="empty-box" style="padding:30px 16px">
        <span class="i">smart_toy</span><h4>还没有学习分身</h4><p>创建一个，开始积累训练数据。</p>
      </div>`;
    } else {
      listHtml = twins.map((twin) => {
        const on = twin.id === activeId;
        const convs = on ? store.state.conversations : [];
        return `
<div class="twin-item ${on ? 'on' : ''}">
  <button data-drawer-twin="${esc(twin.id)}">
    ${twinAvatarHtml(twin)}
    <div class="t-name">${esc(twin.name)}<span class="t-sub">${esc(twin.subject)} · 同步 ${twin.sync_percent || 0}%</span></div>
    <span class="i" style="color:var(--ink-3);font-size:19px">${on ? 'expand_more' : 'chevron_right'}</span>
  </button>
  ${on ? `
  <div class="conv-list">
    ${convs.map((c) => `
    <button class="conv-item ${c.id === store.state.activeConversationId ? 'on' : ''}" data-drawer-conv="${esc(c.id)}">
      <span>${esc(c.title)}</span>
    </button>`).join('')}
    <button class="conv-item" data-drawer-newconv style="color:var(--primary)">
      <span class="i" style="font-size:16px">add</span><span>新对话</span>
    </button>
  </div>` : ''}
</div>`;
      }).join('');
    }
    return `
<div class="drawer-head">
  <div class="drawer-brand">${logoSvg(34, false)}<b>双生</b><span>你的学习分身</span></div>
  <button class="btn primary block" style="height:44px" data-drawer-newtwin><span class="i">add</span>新建分身</button>
</div>
<div class="drawer-list hide-scrollbar">${listHtml}</div>
<div class="drawer-foot">
  <button class="drawer-user" style="width:100%" data-drawer-settings>
    ${userAvatarHtml(user)}
    <div class="nm"><b>${esc(user ? user.display_name : '')}</b><span>${esc(user ? user.email : '')}</span></div>
    <span class="i" style="color:var(--ink-3)">settings</span>
  </button>
</div>`;
  }

  function renderDrawer() {
    const drawer = qs('#drawer');
    drawer.innerHTML = drawerHtml();
    drawer.querySelectorAll('[data-drawer-twin]').forEach((n) => {
      n.onclick = () => selectTwin(n.getAttribute('data-drawer-twin'));
    });
    drawer.querySelectorAll('[data-drawer-conv]').forEach((n) => {
      n.onclick = () => { openConversation(n.getAttribute('data-drawer-conv')); };
    });
    const newConv = drawer.querySelector('[data-drawer-newconv]');
    if (newConv) newConv.onclick = () => { newConversation(); };
    const newTwin = drawer.querySelector('[data-drawer-newtwin]');
    if (newTwin) newTwin.onclick = () => { closeDrawer(); router.go('twin-new'); };
    const toSettings = drawer.querySelector('[data-drawer-settings]');
    if (toSettings) toSettings.onclick = () => { closeDrawer(); router.go('settings'); };
  }

  function openDrawer() {
    renderDrawer();
    qs('#drawer').classList.add('active');
    setScrim(true, closeDrawer);
  }
  function closeDrawer() {
    const drawer = qs('#drawer');
    if (drawer) drawer.classList.remove('active');
    setScrim(false);
  }
  function drawerIsOpen() { return qs('#drawer').classList.contains('active'); }

  /* ================= 数据编排 ================= */
  async function hydrate(knownUser) {
    const [user, twins] = await Promise.all([
      knownUser ? Promise.resolve(knownUser) : api.getMe().catch(() => null),
      api.listTwins().catch(() => []),
    ]);
    let activeTwinId = store.state.activeTwinId;
    if (!twins.some((t) => t.id === activeTwinId)) activeTwinId = twins[0] ? twins[0].id : null;
    store.set({ user, twins, activeTwinId });
    await loadConversations();
  }

  async function refreshTwins() {
    const twins = await api.listTwins().catch(() => store.state.twins);
    let activeTwinId = store.state.activeTwinId;
    if (!twins.some((t) => t.id === activeTwinId)) activeTwinId = twins[0] ? twins[0].id : null;
    store.set({ twins, activeTwinId });
    if (store.state.screen === 'home') window.DSScreens.home.render();
  }

  async function loadConversations() {
    const twin = store.activeTwin();
    if (!twin) { store.set({ conversations: [], activeConversationId: null, messages: [] }); return; }
    const conversations = await api.listConversations(twin.id).catch(() => []);
    let activeConversationId = store.state.activeConversationId;
    if (!conversations.some((c) => c.id === activeConversationId)) activeConversationId = null;
    store.set({ conversations, activeConversationId });
  }

  async function refreshConversations() {
    const twin = store.activeTwin();
    if (!twin) return;
    const conversations = await api.listConversations(twin.id).catch(() => store.state.conversations);
    store.set({ conversations });
    if (store.state.screen === 'home') window.DSScreens.home.render();
  }

  function invalidateTwinScreens() {
    ['route', 'profile', 'review', 'blackboard', 'mistakes'].forEach((k) => {
      const s = window.DSScreens[k];
      if (s && s.invalidate) s.invalidate();
    });
  }

  async function selectTwin(twinId, options) {
    if (twinId === store.state.activeTwinId && !(options && options.force)) { closeDrawer(); return; }
    store.set({ activeTwinId: twinId, activeConversationId: null, messages: [], documents: [] });
    invalidateTwinScreens();
    await loadConversations();
    closeDrawer();
    if (!(options && options.silent)) router.resetTo('home');
    else if (store.state.screen === 'home') window.DSScreens.home.render();
  }

  async function openConversation(convId) {
    closeDrawer();
    store.set({ activeConversationId: convId, messages: [] });
    router.go('chat');
    try {
      const detail = await api.getConversation(convId);
      const convTwinId = detail && detail.conversation ? detail.conversation.twin_id : null;
      if (convTwinId && convTwinId !== store.state.activeTwinId) {
        store.set({ activeTwinId: convTwinId, chatMode: 'twin' });
        await loadConversations();
      }
      store.set({ messages: detail.messages || [] });
      window.DSScreens.chat.renderMessages();
      window.DSScreens.chat.updateHeader();
    } catch (err) { toastError(err); }
  }

  function newConversation() {
    closeDrawer();
    store.set({ activeConversationId: null, messages: [], chatMode: store.activeTwin() ? 'twin' : 'normal' });
    router.go('chat');
  }

  function startChatWith(text) {
    store.set({ activeConversationId: store.state.activeConversationId, chatMode: store.activeTwin() ? 'twin' : 'normal' });
    router.go('chat', { draft: text });
  }

  /* ================= 主题 ================= */
  let themeSwitchTimer = null;
  function setTheme(theme) {
    const html = document.documentElement;
    html.classList.add('theme-switching');
    store.set({ theme });
    html.setAttribute('data-theme', theme);
    clearTimeout(themeSwitchTimer);
    themeSwitchTimer = setTimeout(() => html.classList.remove('theme-switching'), 140);
  }

  /* ================= 进入流程 ================= */
  function enterAuth() { router.resetTo('auth'); }
  function enterApp() { router.resetTo('home'); }

  async function boot() {
    setTheme(store.state.theme);
    // 视口高度（键盘弹起适配）
    const applyVh = () => {
      const h = (window.visualViewport ? window.visualViewport.height : window.innerHeight) * 0.01;
      document.documentElement.style.setProperty('--app-vh', `${h}px`);
      if (window.visualViewport) {
        const inset = Math.max(0, window.innerHeight - window.visualViewport.height - window.visualViewport.offsetTop);
        document.documentElement.style.setProperty('--kb-inset', `${inset}px`);
      }
    };
    applyVh();
    window.addEventListener('resize', applyVh);
    if (window.visualViewport) window.visualViewport.addEventListener('resize', applyVh);

    // 全局错误兜底
    window.addEventListener('unhandledrejection', (event) => {
      console.error(event.reason);
      toastError(event.reason);
    });

    // 挂载所有屏幕
    SCREENS.forEach((id) => {
      const rootEl = qs(`#screen-${id}`);
      const screen = window.DSScreens[id];
      if (rootEl && screen && screen.mount) screen.mount(rootEl);
    });

    // 文档浮层关闭按钮
    qs('#overlay-doc-close').addEventListener('click', () => closeDoc(false));
    qs('#overlay-doc-agree').addEventListener('click', () => closeDoc(true));

    // 启动画面 → 认证/主页
    const splash = qs('#screen-splash');
    const minSplash = new Promise((r) => setTimeout(r, 900));
    let target = 'auth';
    if (api.authed) {
      try { await hydrate(); target = 'home'; }
      catch (err) {
        if (err && err.status === 401) { api.setTokens(null); }
        else if (err && err.isNetwork) { toast('暂时连不上云端，请检查网络', 'err'); }
        target = api.authed ? 'home' : 'auth';
      }
    }
    await minSplash;
    splash.classList.add('leaving');
    setTimeout(() => { splash.classList.remove('active', 'leaving'); splash.style.display = 'none'; }, 320);
    router.resetTo(target);
  }

  /* ================= Android 返回键 ================= */
  const legacyApp = {
    onBackPressed() {
      if (qs('#overlay-doc').classList.contains('active')) { closeDoc(false); return true; }
      if (drawerIsOpen()) { closeDrawer(); return true; }
      if (store.state.screen === 'auth' || store.state.screen === 'splash') return false;
      if (stack.length > 1) { router.back(); return true; }
      if (store.state.screen !== 'home') { router.resetTo('home'); return true; }
      return false;
    },
    navigate(id) { router.go(id); },
    get state() { return store.state; },
  };
  window.app = legacyApp;

  window.DSRouter = router;
  window.DSApp = {
    hydrate, refreshTwins, refreshConversations, loadConversations,
    selectTwin, openConversation, newConversation, startChatWith,
    openDrawer, closeDrawer, setTheme, enterAuth, enterApp,
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
