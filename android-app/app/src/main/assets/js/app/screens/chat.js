/* 双生 · 聊天屏（分身对话 / 普通模式，打字机 + Markdown + 公式） */
(function () {
  'use strict';
  const { qs, esc, markSvg, toast, toastError } = window.DSUi;
  const md = window.DSMarkdown;
  const store = window.DSStore;
  const api = window.DSApi;

  let root;
  let sending = false;

  function headerTitle() {
    const twin = store.activeTwin();
    const mode = store.state.chatMode;
    if (mode === 'normal') return { t: '普通 AI', s: '不使用分身记忆与资料' };
    if (!twin) return { t: '对话', s: '' };
    const conv = store.activeConversation();
    return { t: twin.name, s: conv ? conv.title : '新对话' };
  }

  function bubbleUser(text) {
    return `<div class="msg-row user"><div class="bubble-user">${esc(text)}</div></div>`;
  }

  function bubbleAi(message) {
    const isFallback = message.provider === 'echolearn';
    const meta = [];
    if (message.twin_id || store.state.chatMode === 'twin') meta.push('<span class="chip blue"><span class="i">memory</span>分身记忆</span>');
    if (isFallback) meta.push('<span class="chip amber"><span class="i">cloud_off</span>降级回答</span>');
    else if (message.model) meta.push(`<span class="chip"><span class="i">neurology</span>${esc(message.model)}</span>`);
    return `
<div class="msg-row"><div class="msg-ai">
  <div class="ai-dot">${markSvg()}</div>
  <div class="bubble-ai">
    <div class="md">${md.render(message.content)}</div>
    ${meta.length ? `<div class="meta">${meta.join('')}</div>` : ''}
  </div>
</div></div>`;
  }

  function typingBubble() {
    return `
<div class="msg-row" id="typing-row"><div class="msg-ai">
  <div class="ai-dot">${markSvg()}</div>
  <div class="bubble-ai"><div class="typing-dots"><i></i><i></i><i></i></div></div>
</div></div>`;
  }

  function emptyHtml() {
    const twin = store.activeTwin();
    return `
<div class="empty-box" style="padding-top:9vh">
  <div class="ob-avatar" style="width:84px;height:84px;border-radius:28px;margin-bottom:18px">${markSvg()}</div>
  <h4 style="font-size:var(--fs-lg)">${twin ? `${esc(twin.name)}已就位` : '开始对话'}</h4>
  <p>提出问题、复述知识点，或者让分身<br/>安排今天的训练。每一句话都会成为训练数据。</p>
</div>
<div class="suggest-row" style="margin-top:18px">
  <button class="chip blue clickable" data-suggest="给我安排今天的学习路线">今天怎么学？</button>
  <button class="chip mint clickable" data-suggest="用黑板一步步给我讲一个我最薄弱的知识点">讲个薄弱点</button>
  <button class="chip amber clickable" data-suggest="帮我复盘最近的错题和薄弱环节">复盘错题</button>
</div>`;
  }

  function renderMessages() {
    const box = qs('#chat-list', root);
    const msgs = store.state.messages;
    if (!msgs.length) { box.innerHTML = emptyHtml(); bindSuggests(); return; }
    box.innerHTML = msgs.map((m) => (m.role === 'user' ? bubbleUser(m.content) : bubbleAi(m))).join('');
    md.typeset(box);
    scrollBottom(false);
  }

  function bindSuggests() {
    root.querySelectorAll('[data-suggest]').forEach((n) => {
      n.onclick = () => { qs('#chat-input', root).value = n.getAttribute('data-suggest'); onInput(); send(); };
    });
  }

  function scrollBottom(smooth) {
    const body = qs('#chat-scroll', root);
    body.scrollTo({ top: body.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  }

  function onInput() {
    const input = qs('#chat-input', root);
    input.style.height = 'auto';
    input.style.height = `${Math.min(110, input.scrollHeight)}px`;
    const hasText = input.value.trim().length > 0;
    qs('#chat-send', root).classList.toggle('hidden', !hasText);
    qs('#chat-voice', root).classList.toggle('hidden', hasText);
  }

  async function send() {
    if (sending) return;
    const input = qs('#chat-input', root);
    const text = input.value.trim();
    if (!text) return;
    const mode = store.state.chatMode;
    const twin = store.activeTwin();
    if (mode === 'twin' && !twin) { toast('请先创建学习分身，或切换到普通模式', 'info'); return; }

    sending = true;
    input.value = ''; onInput();
    const box = qs('#chat-list', root);
    if (!store.state.messages.length) box.innerHTML = '';
    store.state.messages.push({ role: 'user', content: text });
    box.insertAdjacentHTML('beforeend', bubbleUser(text));
    box.insertAdjacentHTML('beforeend', typingBubble());
    scrollBottom(true);

    let streamStarted = false;
    try {
      let answer = '';
      let painted = false;
      let paintQueued = false;
      const row = () => qs('#typing-row', root);
      const paint = (force) => {
        const current = row();
        if (!current) return;
        if (!painted) {
          current.querySelector('.bubble-ai').innerHTML = '<div class="md stream-target"></div>';
          painted = true;
        }
        const target = current.querySelector('.stream-target');
        target.innerHTML = md.render(answer || '');
        if (force) md.typeset(current);
        scrollBottom(false);
      };
      const schedulePaint = () => {
        if (paintQueued) return;
        paintQueued = true;
        requestAnimationFrame(() => {
          paintQueued = false;
          paint(false);
        });
      };
      const result = await api.streamMessage({
        message: text,
        conversation_id: store.state.activeConversationId,
        twin_id: mode === 'twin' && twin ? twin.id : null,
        mode,
      }, {
        onStart(meta) {
          streamStarted = true;
          if (!store.state.activeConversationId && meta.conversation_id) {
            store.set({ activeConversationId: meta.conversation_id });
            window.DSApp.refreshConversations();
          }
        },
        onDelta(delta) {
          if (!delta) return;
          answer += delta;
          schedulePaint();
        },
        onDone(done) {
          if (done && done.answer) answer = done.answer;
          paint(true);
        },
      });
      if (!result) throw new Error('流式响应未正常结束，请重试');
      if (!store.state.activeConversationId) {
        store.set({ activeConversationId: result.conversation_id });
        window.DSApp.refreshConversations();
      }
      const aiMsg = { role: 'assistant', content: result.answer || answer, provider: result.provider, model: result.model };
      store.state.messages.push(aiMsg);
      const current = row();
      if (current) {
        current.outerHTML = bubbleAi(aiMsg);
        md.typeset(box);
        scrollBottom(true);
      }
    } catch (err) {
      const row = qs('#typing-row', root);
      if (row) row.remove();
      if (!streamStarted) store.state.messages.pop();
      toastError(err);
      input.value = text; onInput();
    }
    sending = false;
  }

  function setMode(mode) {
    if (store.state.chatMode === mode) return;
    store.set({ chatMode: mode });
    syncModeControls();
    updateHeader();
  }

  function syncModeControls() {
    const mode = store.state.chatMode;
    const seg = qs('#chat-mode-seg', root);
    if (!seg) return;
    seg.classList.toggle('pos-1', mode === 'normal');
    seg.querySelectorAll('button').forEach((b, i) => b.classList.toggle('on', (i === 0) === (mode === 'twin')));
  }

  function updateHeader() {
    const { t, s } = headerTitle();
    qs('#chat-title', root).innerHTML = `${esc(t)}${s ? ` <span class="subtitle">${esc(s)}</span>` : ''}`;
  }

  function toggleVoice(force) {
    const on = force !== undefined ? force : !store.state.voiceListening;
    store.set({ voiceListening: on });
    const btn = qs('#chat-voice', root);
    btn.classList.toggle('listening', on);
    const input = qs('#chat-input', root);
    input.placeholder = on ? '正在听你说…' : '输入你的问题或学习需求…';
    if (on) {
      if (window.DualShengAndroid && window.DualShengAndroid.startVoiceInput) {
        window.DualShengAndroid.startVoiceInput();
      } else {
        store.set({ voiceListening: false });
        btn.classList.remove('listening');
        showVoiceFallback('当前环境不支持系统语音输入');
      }
    } else if (window.DualShengAndroid && window.DualShengAndroid.stopVoiceInput) {
      window.DualShengAndroid.stopVoiceInput();
    }
  }

  function showVoiceFallback(message) {
    const panel = qs('#voice-fallback', root);
    if (!panel) return;
    const note = qs('#voice-fallback-note', panel);
    if (note) note.textContent = message || '语音识别暂不可用';
    panel.classList.remove('hidden');
    const text = qs('#voice-fallback-text', panel);
    if (text) setTimeout(() => text.focus(), 60);
  }

  function hideVoiceFallback() {
    const panel = qs('#voice-fallback', root);
    if (panel) panel.classList.add('hidden');
  }

  function useVoiceFallbackText() {
    const text = (qs('#voice-fallback-text', root).value || '').trim();
    if (!text) { toast('先输入要转写到聊天框的内容', 'info'); return; }
    const input = qs('#chat-input', root);
    input.value = text;
    qs('#voice-fallback-text', root).value = '';
    hideVoiceFallback();
    onInput();
    input.focus();
  }

  // Android 语音桥回调
  window.DualShengVoice = {
    onPartial(text) { const input = qs('#chat-input'); if (input) { input.value = text; onInput(); } },
    onResult(text) { const input = qs('#chat-input'); if (input) { input.value = text; onInput(); } toggleVoice(false); },
    onError(message) { toggleVoice(false); showVoiceFallback(message || '语音输入失败，请再试一次'); },
  };

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="chat-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title" id="chat-title">对话</div>
  <button class="icon-btn" id="chat-menu"><span class="i">menu_open</span></button>
</header>
<div class="chat-body hide-scrollbar" id="chat-scroll">
  <div class="chat-inner" id="chat-list"></div>
</div>
<div class="composer-zone">
  <div class="seg mode" id="chat-mode-seg">
    <div class="seg-thumb"></div>
    <button class="on">分身模式</button>
    <button>普通模式</button>
  </div>
  <div class="voice-fallback hidden" id="voice-fallback">
    <div class="vf-head"><span class="i">mic_off</span><b>语音识别未完成</b><button class="icon-btn" id="voice-fallback-close"><span class="i">close</span></button></div>
    <p id="voice-fallback-note">可以手动输入刚才要说的话。</p>
    <textarea id="voice-fallback-text" rows="2" placeholder="把刚才想说的话写在这里"></textarea>
    <button class="btn primary sm" id="voice-fallback-use" type="button"><span class="i">keyboard_return</span>放入输入框</button>
  </div>
  <div class="composer">
    <button class="icon-btn" id="chat-attach"><span class="i">add</span></button>
    <textarea id="chat-input" rows="1" placeholder="输入你的问题或学习需求…"></textarea>
    <button class="send voice" id="chat-voice"><span class="i" style="font-size:20px">mic</span></button>
    <button class="send hidden" id="chat-send"><span class="i fill" style="font-size:20px">arrow_upward</span></button>
  </div>
</div>`;

    qs('#chat-back', root).addEventListener('click', () => window.DSRouter.go('home'));
    qs('#chat-menu', root).addEventListener('click', () => window.DSApp.openDrawer());
    qs('#chat-attach', root).addEventListener('click', () => window.DSRouter.go('library'));
    qs('#chat-input', root).addEventListener('input', onInput);
    qs('#chat-input', root).addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    qs('#chat-send', root).addEventListener('click', send);
    qs('#chat-voice', root).addEventListener('click', () => toggleVoice());
    qs('#voice-fallback-close', root).addEventListener('click', hideVoiceFallback);
    qs('#voice-fallback-use', root).addEventListener('click', useVoiceFallbackText);
    const seg = qs('#chat-mode-seg', root);
    seg.querySelectorAll('button')[0].addEventListener('click', () => setMode('twin'));
    seg.querySelectorAll('button')[1].addEventListener('click', () => setMode('normal'));
  }

  function show(params) {
    syncModeControls();
    updateHeader();
    renderMessages();
    if (params && params.draft) {
      const input = qs('#chat-input', root);
      input.value = params.draft; onInput();
      setTimeout(send, 60);
    }
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.chat = { mount, show, renderMessages, updateHeader };
})();
