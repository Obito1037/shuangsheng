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
    showNotice(friendlyError(error), '操作未完成');
  }

  function firstInput(selector) {
    return document.querySelector(selector)?.value?.trim() || '';
  }

  function panelInput(panelSelector, index) {
    return document.querySelectorAll(`${panelSelector} input`)[index]?.value?.trim() || '';
  }

  function selectedTwin() {
    return appData.twins.find((item) => item.id === app.state.selectedTwinId) || null;
  }

  const twinRequiredScreens = new Set(['upload-material', 'twin-library', 'learning-route', 'blackboard', 'mistake-review']);
  let originalEmptyTitleHtml = '';
  let originalEmptyDescriptionHtml = '';
  let originalEmptyGridHtml = '';

  function friendlyError(error) {
    const message = error?.message || String(error || '请求失败');
    if (/failed to fetch|networkerror|load failed/i.test(message)) {
      return '暂时无法连接云服务器，请检查网络后重试。';
    }
    return message;
  }

  function installNoticeLayer() {
    if (document.getElementById('dualsheng-notice-style')) return;
    const style = document.createElement('style');
    style.id = 'dualsheng-notice-style';
    style.textContent = `
      .dualsheng-notice-mask {
        position: fixed;
        inset: 0;
        z-index: 9999;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        padding: 24px 18px max(24px, env(safe-area-inset-bottom));
        background: rgba(20, 32, 44, 0.18);
        backdrop-filter: blur(6px);
      }
      .dualsheng-notice-card {
        width: min(100%, 420px);
        border-radius: 24px;
        background: rgba(255, 255, 255, 0.98);
        box-shadow: 0 24px 70px rgba(26, 78, 112, 0.18);
        border: 1px solid rgba(33, 167, 230, 0.12);
        padding: 18px;
      }
      .dualsheng-notice-icon {
        width: 40px;
        height: 40px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #1299df;
        background: #e8f6ff;
        flex: none;
      }
      .dualsheng-notice-title {
        font-size: 16px;
        line-height: 1.35;
        font-weight: 700;
        color: #17212b;
      }
      .dualsheng-notice-message {
        margin-top: 4px;
        font-size: 14px;
        line-height: 1.6;
        color: #5b6773;
      }
      .dualsheng-notice-button {
        min-height: 44px;
        border: 0;
        border-radius: 999px;
        padding: 0 18px;
        background: #14a7e6;
        color: white;
        font-size: 14px;
        font-weight: 700;
      }
    `;
    document.head.appendChild(style);
  }

  function showNotice(message, title = '提示') {
    installNoticeLayer();
    document.getElementById('dualsheng-notice')?.remove();
    const mask = document.createElement('div');
    mask.id = 'dualsheng-notice';
    mask.className = 'dualsheng-notice-mask';
    mask.innerHTML = `
      <div class="dualsheng-notice-card">
        <div class="flex gap-3 items-start">
          <div class="dualsheng-notice-icon">
            <span class="material-symbols-rounded text-[22px]">info</span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="dualsheng-notice-title"></div>
            <div class="dualsheng-notice-message"></div>
          </div>
        </div>
        <div class="flex justify-end mt-5">
          <button class="dualsheng-notice-button">知道了</button>
        </div>
      </div>
    `;
    mask.querySelector('.dualsheng-notice-title').textContent = title;
    mask.querySelector('.dualsheng-notice-message').textContent = message;
    mask.querySelector('button').addEventListener('click', () => mask.remove());
    mask.addEventListener('click', (event) => {
      if (event.target === mask) mask.remove();
    });
    document.body.appendChild(mask);
  }

  function installErrorBoundary() {
    const originalAlert = window.alert;
    window.alert = (message) => showNotice(String(message || ''), '提示');
    window.DualShengNativeAlert = originalAlert;
    window.addEventListener('error', (event) => {
      showNotice('页面遇到了一点问题，已为你回到主界面。', '页面已恢复');
      recoverToMainScreen();
      console.error(event.error || event.message);
    });
    window.addEventListener('unhandledrejection', (event) => {
      showNotice(friendlyError(event.reason), '操作未完成');
      recoverToMainScreen();
      console.error(event.reason);
    });
  }

  function recoverToMainScreen() {
    document.querySelectorAll('.screen').forEach((screen) => {
      screen.classList.remove('active', 'entering', 'leaving');
    });
    document.getElementById('screen-main-chat')?.classList.add('active');
    app.state.currentScreen = 'main-chat';
    app.isAnimating = false;
    app.closeDrawer?.();
    app.toggleUploadSheet?.(false);
  }

  function captureMainTemplates() {
    const heading = document.querySelector('#main-empty-view h2');
    const description = document.querySelector('#main-empty-view p');
    const grid = document.querySelector('#main-empty-view .empty-state-grid');
    originalEmptyTitleHtml = heading?.innerHTML || '';
    originalEmptyDescriptionHtml = description?.innerHTML || '';
    originalEmptyGridHtml = grid?.innerHTML || '';
  }

  function restoreMainTemplates() {
    const heading = document.querySelector('#main-empty-view h2');
    const description = document.querySelector('#main-empty-view p');
    const grid = document.querySelector('#main-empty-view .empty-state-grid');
    if (heading && originalEmptyTitleHtml && !heading.querySelector('#empty-state-title')) {
      heading.innerHTML = originalEmptyTitleHtml;
    }
    if (description && originalEmptyDescriptionHtml) description.innerHTML = originalEmptyDescriptionHtml;
    if (grid && originalEmptyGridHtml && grid.dataset.emptyMode === 'true') {
      grid.innerHTML = originalEmptyGridHtml;
      delete grid.dataset.emptyMode;
    }
  }

  function summaryCard() {
    return document.querySelector('#screen-main-chat main .app-card.rounded-full');
  }

  function setComposerState(hasTwin) {
    const switcher = document.getElementById('ai-mode-switcher');
    const input = document.getElementById('chat-input');
    if (switcher) {
      switcher.classList.toggle('hidden', !hasTwin);
      const buttons = switcher.querySelectorAll('button');
      if (buttons[0]) buttons[0].textContent = '学习分身';
      if (buttons[1]) buttons[1].textContent = '基础模式';
    }
    if (input && !hasTwin) input.placeholder = '先创建学习分身，再开始同步学习...';
    if (input && hasTwin) input.placeholder = '输入你的问题或学习需求...';
  }

  function renderNoTwinState() {
    const emptyView = document.getElementById('main-empty-view');
    const chatView = document.getElementById('main-chat-view');
    const headerTitle = document.getElementById('main-header-title');
    const headerIcon = document.getElementById('main-header-icon');
    const emptyIcon = document.getElementById('empty-state-icon');
    const chatIcon = document.getElementById('chat-twin-icon');
    const heading = document.querySelector('#main-empty-view h2');
    const description = document.querySelector('#main-empty-view p');
    const grid = document.querySelector('#main-empty-view .empty-state-grid');

    if (headerTitle) headerTitle.textContent = '当前无可用分身';
    if (headerIcon) headerIcon.textContent = 'school';
    if (emptyIcon) emptyIcon.textContent = 'school';
    if (chatIcon) chatIcon.textContent = 'school';
    if (heading) heading.innerHTML = '当前无可用分身';
    if (description) description.textContent = '创建学习分身后，就可以上传资料、规划路线和复盘薄弱点。';
    if (grid) {
      grid.dataset.emptyMode = 'true';
      grid.innerHTML = `
        <button class="app-card p-5 text-left flex flex-col gap-3 btn-press transition-colors-fast hover:border-brand-blue/20 border border-transparent focus:outline-none col-span-2" type="button" data-create-twin-empty>
          <div class="icon-box bg-blue-50 text-brand-blue mb-1">
            <span class="material-symbols-rounded text-[24px]">add_circle</span>
          </div>
          <div>
            <h3 class="font-semibold text-[15px] text-on-surface mb-1">创建学习分身</h3>
            <p class="text-[12px] text-on-surface-variant leading-tight">先建立一个专属分身，再开始训练和同步。</p>
          </div>
        </button>
      `;
      grid.querySelector('[data-create-twin-empty]')?.addEventListener('click', () => app.navigate('create-twin'));
    }
    summaryCard()?.classList.add('hidden');
    setComposerState(false);
    emptyView?.classList.add('active');
    chatView?.classList.remove('active');
  }

  function renderHasTwinState() {
    restoreMainTemplates();
    summaryCard()?.classList.remove('hidden');
    setComposerState(true);
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
        renderNoTwinState();
        return;
      }
      renderHasTwinState();
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

    const registerCodeButton = document.querySelectorAll('#panel-register .m3-input button')[0];
    registerCodeButton?.addEventListener('click', async (event) => {
      event.preventDefault();
      const email = panelInput('#panel-register', 0);
      if (!email) {
        window.alert('请输入邮箱。');
        return;
      }
      const originalText = registerCodeButton.textContent;
      registerCodeButton.disabled = true;
      registerCodeButton.textContent = '发送中';
      try {
        await api.sendEmailCode(email, 'register');
        window.alert('验证码已发送，请查收邮箱。');
      } catch (error) {
        alertError(error);
      } finally {
        registerCodeButton.disabled = false;
        registerCodeButton.textContent = originalText;
      }
    });

    document.querySelector('#panel-register form')?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const email = panelInput('#panel-register', 0);
      const emailCode = panelInput('#panel-register', 1);
      const password = firstInput('#reg-password');
      if (!email || !emailCode || !password) {
        window.alert('请输入邮箱、验证码和密码。');
        return;
      }
      try {
        const result = await api.register(email, password, email.split('@')[0], emailCode);
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
      const originalText = button.textContent;
      button.disabled = true;
      button.textContent = '正在同步';
      try {
        await api.createTwin({ name, subject, goal });
        await hydrateAppData();
        app.renderSidebar();
        app.updateMainView();
        app.navigate('main-chat');
        showNotice('学习分身已创建，并已同步到云端。', '创建成功');
      } catch (error) {
        alertError(error);
      } finally {
        button.disabled = false;
        button.textContent = originalText;
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
      try {
        if (!document.getElementById(`screen-${screenId}`)) {
          showNotice('这个页面暂时不可用，请稍后再试。', '无法打开页面');
          recoverToMainScreen();
          return;
        }
        if (twinRequiredScreens.has(screenId) && !selectedTwin()) {
          showNotice('您尚未创建学习分身，先创建一个再继续。', '需要学习分身');
          original('create-twin');
          return;
        }
        original(screenId);
        setTimeout(() => renderLearning(screenId), 360);
      } catch (error) {
        console.error(error);
        showNotice('页面打开失败，已为你回到主界面。', '页面已恢复');
        recoverToMainScreen();
      }
    };
  }

  ready(async () => {
    ensureAppGlobals();
    captureMainTemplates();
    installErrorBoundary();
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
