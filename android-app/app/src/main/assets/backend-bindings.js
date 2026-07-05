(function () {
  const api = window.DualShengApiClient;
  if (!api) return;

  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  function alertError(error) {
    const message = error?.message || 'Request failed';
    window.alert(message);
  }

  function firstInput(selector) {
    return document.querySelector(selector)?.value?.trim() || '';
  }

  function selectedTwin() {
    return appData.twins.find((item) => item.id === app.state.selectedTwinId) || null;
  }

  function mapTwin(twin, index) {
    const colors = ['blue', 'green', 'purple'];
    const subjectIcon = {
      math: 'functions',
      数学: 'functions',
      english: 'font_download',
      英语: 'font_download',
      programming: 'code',
      编程: 'code',
    };
    return {
      id: twin.id,
      name: twin.name || '学习分身',
      icon: subjectIcon[twin.subject] || 'school',
      color: colors[index % colors.length],
      conversations: [],
      raw: twin,
    };
  }

  function mapConversation(item) {
    return {
      id: item.id,
      title: item.title || '新对话',
      time: item.updated_at ? new Date(item.updated_at).toLocaleDateString() : '刚刚',
      raw: item,
    };
  }

  function ensureAppGlobals() {
    try { window.app = app; } catch (_) {}
    try { window.appData = appData; } catch (_) {}
  }

  async function hydrateAppData(user) {
    ensureAppGlobals();
    const [twins, conversations] = await Promise.all([
      api.listTwins(),
      api.listConversations().catch(() => []),
      api.getUsage().catch(() => null),
      user ? Promise.resolve(user) : api.getMe().catch(() => null),
    ]);

    appData.twins = (twins || []).map(mapTwin);
    const mappedConversations = (conversations || []).map(mapConversation);
    if (appData.twins[0]) {
      appData.twins[0].conversations = mappedConversations;
      app.state.selectedTwinId = appData.twins[0].id;
      app.state.selectedConversationId = mappedConversations[0]?.id || null;
    } else {
      app.state.selectedTwinId = null;
      app.state.selectedConversationId = null;
    }

    app.renderSidebar();
    app.updateMainView();
  }

  function patchEmptyState() {
    const original = app.updateMainView.bind(app);
    app.updateMainView = function () {
      if (!appData.twins.length || !selectedTwin()) {
        const emptyView = document.getElementById('main-empty-view');
        const chatView = document.getElementById('main-chat-view');
        const headerTitle = document.getElementById('main-header-title');
        const emptyTitle = document.getElementById('empty-state-title');
        const headerIcon = document.getElementById('main-header-icon');
        const emptyIcon = document.getElementById('empty-state-icon');
        const chatIcon = document.getElementById('chat-twin-icon');
        if (headerTitle) headerTitle.innerText = '暂无学习分身';
        if (emptyTitle) emptyTitle.innerText = '暂无学习分身';
        if (headerIcon) headerIcon.innerText = 'school';
        if (emptyIcon) emptyIcon.innerText = 'school';
        if (chatIcon) chatIcon.innerText = 'school';
        emptyView?.classList.add('active');
        chatView?.classList.remove('active');
        return;
      }
      original();
    };
  }

  function bindAuth() {
    const originalLoginSuccess = window.loginSuccess;
    window.loginSuccess = async function () {
      const account = firstInput('#panel-login_password input[type="text"]');
      const password = firstInput('#login-password');
      if (!account || !password) {
        window.alert('请输入账号和密码。');
        return;
      }
      try {
        const result = await api.login(account, password);
        api.setTokens(result.tokens);
        await hydrateAppData(result.user);
        originalLoginSuccess();
      } catch (error) {
        alertError(error);
      }
    };

    document.querySelector('#panel-login_password form')?.addEventListener('submit', (event) => {
      event.preventDefault();
      window.loginSuccess();
    });

    document.querySelector('#panel-register form')?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const email = firstInput('#panel-register input[type="text"]');
      const password = firstInput('#reg-password');
      if (!email || !password) {
        window.alert('请输入邮箱和密码。');
        return;
      }
      try {
        const result = await api.register(email, password, email.split('@')[0]);
        api.setTokens(result.tokens);
        await hydrateAppData(result.user);
        originalLoginSuccess();
      } catch (error) {
        alertError(error);
      }
    });
  }

  function bindCreateTwin() {
    const button = document.querySelector('#screen-create-twin main button.bg-brand-blue');
    button?.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      const name = firstInput('#screen-create-twin input') || '学习分身';
      const subject = firstInput('#screen-create-twin select') || '通用学习';
      const goal = firstInput('#screen-create-twin textarea') || '持续学习';
      try {
        const twin = await api.createTwin({ name, subject, goal });
        const mapped = mapTwin(twin, appData.twins.length);
        appData.twins.unshift(mapped);
        app.state.selectedTwinId = mapped.id;
        app.state.selectedConversationId = null;
        app.renderSidebar();
        app.updateMainView();
        app.navigate('main-chat');
      } catch (error) {
        alertError(error);
      }
    }, true);
  }

  function patchChat() {
    const original = app.sendMessage.bind(app);
    app.sendMessage = async function () {
      const input = document.getElementById('chat-input');
      const text = input?.value?.trim();
      if (!text) return;
      if (!api.tokens?.access_token) {
        original();
        return;
      }
      const loading = document.getElementById('loading-message');
      loading?.classList.remove('hidden');
      const previousConversationId = app.state.selectedConversationId;
      original();
      try {
        const result = await api.sendMessage({ message: text, conversation_id: previousConversationId || null });
        const twin = selectedTwin();
        if (twin) {
          const existing = twin.conversations.find((item) => item.id === result.conversation_id);
          if (!existing) {
            twin.conversations.unshift({ id: result.conversation_id, title: text, time: '刚刚' });
          }
          app.state.selectedConversationId = result.conversation_id;
          app.renderSidebar();
          app.updateMainView();
        }
      } catch (error) {
        alertError(error);
      } finally {
        loading?.classList.add('hidden');
      }
    };
  }

  function bindUpload() {
    const input = document.getElementById('material-file-input');
    input?.addEventListener('change', async (event) => {
      const files = Array.from(event.target.files || []);
      if (!files.length || !api.tokens?.access_token) return;
      for (const file of files) {
        try {
          const result = await api.uploadFile(file);
          const fileId = result?.file?.id || result?.id;
          if (fileId) api.parseDocument(fileId).catch(() => null);
        } catch (error) {
          alertError(error);
          break;
        }
      }
    });
  }

  async function renderLibrary() {
    if (!api.tokens?.access_token) return;
    const container = document.querySelector('#screen-twin-library .space-y-3');
    if (!container) return;
    try {
      const documents = await api.listDocuments();
      container.innerHTML = (documents || []).map((doc) => `
        <div class="app-card p-4 flex items-start gap-4">
          <div class="w-12 h-12 rounded-xl bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
            <span class="material-symbols-rounded">description</span>
          </div>
          <div class="flex-1">
            <h4 class="font-medium text-on-surface mb-1">${doc.title || doc.original_name || '学习资料'}</h4>
            <p class="text-xs text-on-surface-variant mb-2">${doc.parse_status || doc.status || 'uploaded'} · ${doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '刚刚'}</p>
            <div class="flex gap-2">
              <span class="px-2 py-0.5 bg-brand-surface rounded text-[10px] text-on-surface-variant">${doc.content_type || 'document'}</span>
            </div>
          </div>
          <button class="text-outline-variant focus:outline-none"><span class="material-symbols-rounded">more_vert</span></button>
        </div>
      `).join('') || container.innerHTML;
    } catch (_) {}
  }

  async function renderLearning(screenId) {
    if (!api.tokens?.access_token || !app.state.selectedTwinId) return;
    try {
      if (screenId === 'twin-library') await renderLibrary();
      if (screenId === 'learning-route') await api.simulateTwin(app.state.selectedTwinId);
      if (screenId === 'mistake-review') await api.getWeakPoints(app.state.selectedTwinId);
      if (screenId === 'blackboard') await api.getBlackboard(app.state.selectedTwinId, null);
    } catch (_) {}
  }

  function patchNavigate() {
    const original = app.navigate.bind(app);
    app.navigate = function (screenId) {
      original(screenId);
      setTimeout(() => renderLearning(screenId), 360);
    };
  }

  ready(async () => {
    ensureAppGlobals();
    patchEmptyState();
    bindAuth();
    bindCreateTwin();
    patchChat();
    bindUpload();
    patchNavigate();
    if (api.tokens?.access_token) {
      try { await hydrateAppData(); } catch (_) { api.setTokens(null); }
    }
  });
})();
