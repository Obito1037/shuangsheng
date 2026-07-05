(function () {
  const api = window.DualShengApiClient;
  if (!api) return;

  const twinRequiredScreens = new Set(['upload-material', 'twin-library', 'learning-route', 'blackboard', 'mistake-review']);
  let originalEmptyTitleHtml = '';
  let originalEmptyDescriptionHtml = '';
  let originalEmptyGridHtml = '';
  let activeMessages = [];

  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  function firstInput(selector) {
    return document.querySelector(selector)?.value?.trim() || '';
  }

  function panelInput(panelSelector, index) {
    return document.querySelectorAll(`${panelSelector} input`)[index]?.value?.trim() || '';
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[char]));
  }

  function friendlyError(error) {
    const message = error?.message || String(error || '请求失败');
    if (/failed to fetch|networkerror|load failed/i.test(message)) {
      return '暂时无法连接云服务器，请检查网络后重试。';
    }
    if (/401|unauthorized|credential|token/i.test(message)) {
      return '登录状态已失效，请重新登录。';
    }
    return message;
  }

  function selectedTwin() {
    return appData.twins.find((item) => item.id === app.state.selectedTwinId) || null;
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

  function alertError(error) {
    showNotice(friendlyError(error), '操作未完成');
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
      #chat-twin-icon { display: none; }
      #chat-twin-icon + * { margin-left: 0; }
    `;
    document.head.appendChild(style);
  }

  function installErrorBoundary() {
    window.alert = (message) => showNotice(String(message || ''), '提示');
    window.addEventListener('error', (event) => {
      console.error(event.error || event.message);
      showNotice('页面遇到了一点问题，已为你回到主界面。', '页面已恢复');
      showScreen('main-chat');
    });
    window.addEventListener('unhandledrejection', (event) => {
      console.error(event.reason);
      showNotice(friendlyError(event.reason), '操作未完成');
    });
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
    await renderSelectedConversation();
    app.updateMainView();
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
    if (heading && originalEmptyTitleHtml && !heading.querySelector('#empty-state-title')) heading.innerHTML = originalEmptyTitleHtml;
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
    if (input) input.placeholder = hasTwin ? '输入你的问题或学习需求...' : '先创建学习分身，再开始同步学习...';
  }

  function renderNoTwinState() {
    const emptyView = document.getElementById('main-empty-view');
    const chatView = document.getElementById('main-chat-view');
    const headerTitle = document.getElementById('main-header-title');
    const headerIcon = document.getElementById('main-header-icon');
    const emptyIcon = document.getElementById('empty-state-icon');
    const heading = document.querySelector('#main-empty-view h2');
    const description = document.querySelector('#main-empty-view p');
    const grid = document.querySelector('#main-empty-view .empty-state-grid');

    if (headerTitle) headerTitle.textContent = '当前无可用分身';
    if (headerIcon) headerIcon.textContent = 'school';
    if (emptyIcon) emptyIcon.textContent = 'school';
    if (heading) heading.textContent = '当前无可用分身';
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

  function replaceSidebarBrandIcon() {
    const box = document.querySelector('#drawer .p-6 .flex.items-center.gap-3.mb-6 > div');
    if (!box) return;
    box.className = 'w-9 h-9 rounded-xl bg-brand-blue flex items-center justify-center overflow-hidden shadow-sm';
    box.innerHTML = '<img alt="双生" class="w-full h-full object-cover" src="https://appassets.androidplatform.net/res/mipmap/ic_launcher.png" />';
  }

  function renderSidebar() {
    replaceSidebarBrandIcon();
    const container = document.getElementById('sidebar-twins-list');
    if (!container) return;
    if (!appData.twins.length) {
      container.innerHTML = `
        <div class="px-2 py-8 text-center text-on-surface-variant">
          <div class="w-14 h-14 mx-auto mb-3 rounded-2xl bg-brand-surface flex items-center justify-center text-brand-blue">
            <span class="material-symbols-rounded">school</span>
          </div>
          <p class="text-sm">您尚未创建学习分身</p>
        </div>
      `;
      return;
    }

    let html = '<div class="space-y-4">';
    appData.twins.forEach((twin) => {
      const isActiveTwin = app.state.selectedTwinId === twin.id;
      html += `
        <div class="${isActiveTwin ? 'twin-item-active' : ''}">
          <button class="w-full flex items-center justify-between p-3 focus:outline-none rounded-[16px] ${isActiveTwin ? 'bg-brand-surface' : 'hover:bg-brand-surface'}" data-twin-id="${escapeHtml(twin.id)}">
            <div class="flex items-center gap-3 min-w-0">
              <div class="icon-box bg-${twin.color}-50 text-${twin.color}-500 shrink-0">
                <span class="material-symbols-rounded text-[20px]">${escapeHtml(twin.icon)}</span>
              </div>
              <span class="font-semibold text-[15px] text-on-surface truncate">${escapeHtml(twin.name)}</span>
            </div>
            <span class="material-symbols-rounded text-outline-variant text-[20px] ${isActiveTwin ? 'rotate-90 text-brand-blue' : ''}">chevron_right</span>
          </button>
      `;
      if (isActiveTwin) {
        html += '<div class="pl-14 pr-2 pb-2 pt-2 space-y-1 relative before:absolute before:left-[35px] before:top-0 before:bottom-4 before:w-[2px] before:bg-outline-variant/10">';
        twin.conversations.forEach((conv) => {
          const active = app.state.selectedConversationId === conv.id;
          html += `
            <button class="w-full flex items-center justify-between p-2.5 rounded-[12px] text-left focus:outline-none hover:bg-brand-surface transition-colors-fast conv-item ${active ? 'conv-item-active' : ''}" data-conversation-id="${escapeHtml(conv.id)}">
              <span class="text-[14px] truncate">${escapeHtml(conv.title)}</span>
            </button>
          `;
        });
        html += `
          <button class="w-full flex items-center gap-2 p-2.5 rounded-[12px] text-left text-on-surface-variant hover:text-brand-blue hover:bg-brand-surface transition-colors-fast focus:outline-none mt-1" data-new-conversation>
            <span class="material-symbols-rounded text-[18px]">add</span>
            <span class="text-[14px] font-medium">新对话</span>
          </button>
        </div>`;
      }
      html += '</div>';
    });
    html += '</div>';
    container.innerHTML = html;

    container.querySelectorAll('[data-twin-id]').forEach((button) => {
      button.addEventListener('click', () => app.selectTwin(button.getAttribute('data-twin-id')));
    });
    container.querySelectorAll('[data-conversation-id]').forEach((button) => {
      button.addEventListener('click', () => app.selectConversation(button.getAttribute('data-conversation-id')));
    });
    container.querySelector('[data-new-conversation]')?.addEventListener('click', () => app.selectConversation(null));
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
      if (app.state.selectedConversationId) {
        renderConversationMessages(activeMessages);
      }
      hideChatAvatar();
    };
  }

  function hideChatAvatar() {
    const icon = document.getElementById('chat-twin-icon');
    const wrapper = icon?.closest('.w-10');
    if (wrapper) wrapper.style.display = 'none';
  }

  function renderConversationMessages(messages) {
    const chatView = document.getElementById('main-chat-view');
    if (!chatView) return;
    if (!messages.length) {
      chatView.innerHTML = `
        <div class="app-card p-5 text-center">
          <h3 class="font-semibold text-on-surface mb-2">新对话已准备好</h3>
          <p class="text-sm text-on-surface-variant">输入一个问题，学习分身会把后续消息都归到这个对话里。</p>
        </div>
      `;
      chatView.classList.add('active');
      return;
    }
    chatView.innerHTML = messages.map((message) => {
      const content = escapeHtml(message.content).replace(/\n/g, '<br/>');
      if (message.role === 'user') {
        return `
          <div class="flex justify-end w-full">
            <div class="max-w-[85%] bg-brand-surface text-on-surface p-4 rounded-[24px] rounded-tr-[8px] text-[15px] leading-relaxed border border-brand-blue/5 shadow-sm">${content}</div>
          </div>
        `;
      }
      return `
        <div class="flex w-full">
          <div class="flex-1 app-card p-5 rounded-tl-[8px]">
            <p class="text-[15px] text-on-surface leading-relaxed">${content}</p>
          </div>
        </div>
      `;
    }).join('');
    chatView.classList.add('active');
  }

  async function renderSelectedConversation() {
    const conversationId = app.state.selectedConversationId;
    if (!conversationId || !api.tokens?.access_token) {
      activeMessages = [];
      return;
    }
    const detail = await api.getConversation(conversationId).catch(() => null);
    activeMessages = detail?.messages || [];
    renderConversationMessages(activeMessages);
  }

  async function refreshConversations() {
    const twin = selectedTwin();
    if (!twin) return;
    twin.conversations = (await api.listConversations()).map(mapConversation);
    if (!twin.conversations.some((item) => item.id === app.state.selectedConversationId)) {
      app.state.selectedConversationId = twin.conversations[0]?.id || null;
    }
    app.renderSidebar();
  }

  async function ensureConversation(title) {
    const twin = selectedTwin();
    if (!twin) throw new Error('请先创建学习分身。');
    if (app.state.selectedConversationId) return app.state.selectedConversationId;
    const conversation = await api.createConversation(title || '新对话');
    twin.conversations.unshift(mapConversation(conversation));
    app.state.selectedConversationId = conversation.id;
    app.renderSidebar();
    return conversation.id;
  }

  function patchChat() {
    app.sendMessage = async function () {
      const input = document.getElementById('chat-input');
      const text = input?.value?.trim();
      if (!text) return;
      if (!api.tokens?.access_token) {
        showNotice('请先登录后再开始对话。');
        return;
      }
      try {
        const conversationId = await ensureConversation(text.slice(0, 30) || '新对话');
        input.value = '';
        app.handleInput();
        activeMessages.push({ role: 'user', content: text });
        activeMessages.push({ role: 'assistant', content: '正在思考...' });
        renderConversationMessages(activeMessages);
        const result = await api.sendMessage({ message: text, conversation_id: conversationId });
        await refreshConversations();
        await renderSelectedConversation();
        if (!activeMessages.length) {
          activeMessages = [
            { role: 'user', content: text },
            { role: 'assistant', content: result.answer },
          ];
          renderConversationMessages(activeMessages);
        }
        app.updateMainView();
      } catch (error) {
        alertError(error);
      }
    };
  }

  function patchSidebarActions() {
    app.renderSidebar = renderSidebar;
    app.selectTwin = async function (twinId) {
      if (app.state.selectedTwinId === twinId) return;
      app.state.selectedTwinId = twinId;
      const twin = selectedTwin();
      app.state.selectedConversationId = twin?.conversations[0]?.id || null;
      app.renderSidebar();
      await renderSelectedConversation();
      app.updateMainView();
      app.closeDrawer();
    };
    app.selectConversation = async function (convId) {
      try {
        if (convId === null) {
          const conversation = await api.createConversation('新对话');
          const twin = selectedTwin();
          twin?.conversations.unshift(mapConversation(conversation));
          app.state.selectedConversationId = conversation.id;
          activeMessages = [];
        } else {
          app.state.selectedConversationId = convId;
          await renderSelectedConversation();
        }
        app.renderSidebar();
        app.updateMainView();
        app.closeDrawer();
      } catch (error) {
        alertError(error);
      }
    };
  }

  function showScreen(screenId) {
    const next = document.getElementById(`screen-${screenId}`);
    if (!next) return false;
    document.querySelectorAll('.screen').forEach((screen) => {
      screen.classList.remove('active', 'entering', 'leaving');
      screen.style.backgroundColor = '';
    });
    next.classList.add('active');
    if (next.classList.contains('sub-screen') && screenId !== 'blackboard') {
      next.style.backgroundColor = '#F7FBFF';
    }
    app.state.currentScreen = screenId;
    app.isAnimating = false;
    app.closeDrawer?.();
    app.toggleUploadSheet?.(false);
    return true;
  }

  function patchNavigate() {
    app.navigate = function (screenId) {
      try {
        if (!document.getElementById(`screen-${screenId}`)) {
          showNotice('这个页面暂时不可用，请稍后再试。', '无法打开页面');
          showScreen('main-chat');
          return;
        }
        if (twinRequiredScreens.has(screenId) && !selectedTwin()) {
          showNotice('您尚未创建学习分身，先创建一个再继续。', '需要学习分身');
          showScreen('create-twin');
          return;
        }
        showScreen(screenId);
        setTimeout(() => renderLearning(screenId), 0);
      } catch (error) {
        console.error(error);
        showNotice('页面打开失败，已为你回到主界面。', '页面已恢复');
        showScreen('main-chat');
      }
    };
  }

  function bindAuth() {
    const originalLoginSuccess = window.loginSuccess;
    window.loginSuccess = async function () {
      const account = firstInput('#panel-login_password input[type="text"]');
      const password = firstInput('#login-password');
      if (!account || !password) {
        showNotice('请输入账号和密码。');
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

    const smsCodeButton = document.querySelectorAll('#panel-login_sms .m3-input button')[0];
    smsCodeButton?.addEventListener('click', async (event) => {
      event.preventDefault();
      const email = panelInput('#panel-login_sms', 0);
      if (!email || !email.includes('@')) {
        showNotice('验证码登录当前支持邮箱，请输入邮箱地址。');
        return;
      }
      const originalText = smsCodeButton.textContent;
      smsCodeButton.disabled = true;
      smsCodeButton.textContent = '发送中';
      try {
        await api.sendEmailCode(email, 'login');
        showNotice('验证码已发送，请查收邮箱。');
      } catch (error) {
        alertError(error);
      } finally {
        smsCodeButton.disabled = false;
        smsCodeButton.textContent = originalText;
      }
    });

    document.querySelector('#panel-login_sms form')?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const email = panelInput('#panel-login_sms', 0);
      const code = panelInput('#panel-login_sms', 1);
      if (!email || !code) {
        showNotice('请输入邮箱和验证码。');
        return;
      }
      try {
        const result = await api.loginWithEmailCode(email, code);
        api.setTokens(result.tokens);
        await hydrateAppData(result.user);
        originalLoginSuccess();
      } catch (error) {
        alertError(error);
      }
    });

    const registerCodeButton = document.querySelectorAll('#panel-register .m3-input button')[0];
    registerCodeButton?.addEventListener('click', async (event) => {
      event.preventDefault();
      const email = panelInput('#panel-register', 0);
      if (!email) {
        showNotice('请输入邮箱。');
        return;
      }
      const originalText = registerCodeButton.textContent;
      registerCodeButton.disabled = true;
      registerCodeButton.textContent = '发送中';
      try {
        await api.sendEmailCode(email, 'register');
        showNotice('验证码已发送，请查收邮箱。');
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
        showNotice('请输入邮箱、验证码和密码。');
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
        showScreen('main-chat');
        showNotice('学习分身已创建，并已同步到云端。', '创建成功');
      } catch (error) {
        alertError(error);
      } finally {
        button.disabled = false;
        button.textContent = originalText;
      }
    }, true);
  }

  function bindUpload() {
    const input = document.getElementById('material-file-input');
    if (!input) return;
    input.addEventListener('change', async (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      const files = Array.from(event.target.files || []);
      input.value = '';
      if (!files.length) return;
      if (!api.tokens?.access_token) {
        showNotice('请先登录后再上传资料。');
        return;
      }
      try {
        showNotice(`开始上传 ${files.length} 个文件。`, '上传资料');
        for (const file of files) {
          const result = await api.uploadFile(file);
          const fileId = result?.file?.id || result?.id;
          if (fileId) await api.parseDocument(fileId).catch(() => null);
        }
        await renderLibrary();
        showNotice('文件已上传并进入资料库训练流程。', '上传完成');
      } catch (error) {
        alertError(error);
      }
    }, true);

    document.querySelector('#screen-upload-material button.bg-brand-blue')?.addEventListener('click', (event) => {
      event.preventDefault();
      app.pickFiles('.pdf,.doc,.docx,.ppt,.pptx,.txt,.md,image/*,.wav,.mp3,.m4a');
    });
  }

  function patchVoice() {
    window.DualShengVoice = {
      onPartial(text) {
        const input = document.getElementById('chat-input');
        if (input) {
          input.value = text;
          app.handleInput();
        }
      },
      onResult(text) {
        const input = document.getElementById('chat-input');
        if (input) {
          input.value = text;
          app.handleInput();
        }
        app.toggleVoice(false);
      },
      onError(message) {
        app.toggleVoice(false);
        showNotice(message || '语音输入失败，请再试一次。');
      },
    };

    app.toggleVoice = function (forceState) {
      const nextState = forceState !== undefined ? forceState : !app.state.isVoiceListening;
      const btn = document.getElementById('btn-voice');
      const input = document.getElementById('chat-input');
      app.state.isVoiceListening = nextState;
      btn?.classList.toggle('listening', nextState);
      if (input) input.placeholder = nextState ? '正在听你说...' : '输入你的问题或学习需求...';
      if (nextState) {
        if (window.DualShengAndroid?.startVoiceInput) {
          window.DualShengAndroid.startVoiceInput();
        } else {
          app.state.isVoiceListening = false;
          btn?.classList.remove('listening');
          showNotice('当前环境不支持语音输入，请在 Android App 中使用。');
        }
      } else {
        window.DualShengAndroid?.stopVoiceInput?.();
      }
    };
  }

  async function renderLibrary() {
    if (!api.tokens?.access_token) return;
    const container = document.querySelector('#screen-twin-library .space-y-3');
    if (!container) return;
    try {
      const documents = await api.listDocuments();
      if (!documents?.length) {
        container.innerHTML = '<div class="app-card p-4 text-center text-sm text-on-surface-variant">资料库暂无内容，请先上传文件训练。</div>';
        return;
      }
      container.innerHTML = documents.map((doc) => `
        <div class="app-card p-4 flex items-start gap-4">
          <div class="w-12 h-12 rounded-xl bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
            <span class="material-symbols-rounded">description</span>
          </div>
          <div class="flex-1">
            <h4 class="font-medium text-on-surface mb-1">${escapeHtml(doc.title || doc.original_name || '学习资料')}</h4>
            <p class="text-xs text-on-surface-variant mb-2">${escapeHtml(doc.parse_status || doc.status || 'uploaded')} · ${doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '刚刚'}</p>
            <div class="flex gap-2">
              <span class="px-2 py-0.5 bg-brand-surface rounded text-[10px] text-on-surface-variant">${escapeHtml(doc.content_type || 'document')}</span>
            </div>
          </div>
        </div>
      `).join('');
    } catch (error) {
      alertError(error);
    }
  }

  async function renderLearning(screenId) {
    if (!api.tokens?.access_token || !app.state.selectedTwinId) return;
    try {
      if (screenId === 'twin-library') await renderLibrary();
      if (screenId === 'learning-route') await api.simulateTwin(app.state.selectedTwinId);
      if (screenId === 'mistake-review') await api.getWeakPoints(app.state.selectedTwinId);
      if (screenId === 'blackboard') await api.getBlackboard(app.state.selectedTwinId, null);
    } catch (error) {
      alertError(error);
    }
  }

  ready(async () => {
    ensureAppGlobals();
    captureMainTemplates();
    installNoticeLayer();
    installErrorBoundary();
    patchSidebarActions();
    patchEmptyState();
    bindAuth();
    bindCreateTwin();
    patchChat();
    bindUpload();
    patchVoice();
    patchNavigate();
    replaceSidebarBrandIcon();
    if (api.tokens?.access_token) {
      try {
        await hydrateAppData();
      } catch (error) {
        api.setTokens(null);
        alertError(error);
      }
    } else {
      appData.twins = [];
      app.state.selectedTwinId = null;
      app.state.selectedConversationId = null;
      app.renderSidebar();
      app.updateMainView();
    }
  });
})();
