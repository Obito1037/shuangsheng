/* 双生 · 全局状态（单一数据源 + 订阅） */
(function () {
  'use strict';

  const PERSIST_KEY = 'dualsheng.ui';

  function readPersist() {
    try { return JSON.parse(localStorage.getItem(PERSIST_KEY) || '{}'); } catch (_) { return {}; }
  }

  const persisted = readPersist();

  const state = {
    user: null,
    usage: null,
    twins: [],                 // LearningTwinRead[]
    activeTwinId: persisted.activeTwinId || null,
    conversations: [],         // 当前分身下的会话
    activeConversationId: null,
    messages: [],              // 当前会话消息
    documents: [],             // 当前分身资料
    uploadQueue: [],           // {name, state: uploading|parsing|done|failed, note}
    chatMode: 'twin',          // twin | normal
    theme: persisted.theme || 'light',
    voiceListening: false,
    screen: 'splash',
  };

  const listeners = new Set();

  function persist() {
    try {
      localStorage.setItem(PERSIST_KEY, JSON.stringify({ activeTwinId: state.activeTwinId, theme: state.theme }));
    } catch (_) { /* ignore */ }
  }

  const store = {
    state,
    get(name) { return state[name]; },
    set(patch) {
      Object.assign(state, patch);
      if ('activeTwinId' in patch || 'theme' in patch) persist();
      listeners.forEach((fn) => { try { fn(state, patch); } catch (err) { console.error(err); } });
    },
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    activeTwin() { return state.twins.find((t) => t.id === state.activeTwinId) || null; },
    activeConversation() { return state.conversations.find((c) => c.id === state.activeConversationId) || null; },
    reset() {
      this.set({
        user: null, usage: null, twins: [], activeTwinId: null,
        conversations: [], activeConversationId: null, messages: [],
        documents: [], uploadQueue: [], chatMode: 'twin',
      });
    },
  };

  window.DSStore = store;
})();
