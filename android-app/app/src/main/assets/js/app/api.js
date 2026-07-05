/* 双生 · API 客户端（唯一网络出口） */
(function () {
  'use strict';

  const TOKEN_KEY = 'dualsheng.tokens';
  const isAppAssets = location.hostname === 'appassets.androidplatform.net';

  function readTokens() {
    try { return JSON.parse(localStorage.getItem(TOKEN_KEY) || 'null'); } catch (_) { return null; }
  }

  const api = {
    baseUrl: isAppAssets ? 'http://8.148.69.255' : 'http://127.0.0.1:8000',
    tokens: readTokens(),

    setTokens(tokens) {
      this.tokens = tokens || null;
      if (this.tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(this.tokens));
      else localStorage.removeItem(TOKEN_KEY);
    },
    get authed() { return Boolean(this.tokens && this.tokens.access_token); },

    async request(path, options = {}) {
      const headers = new Headers(options.headers || {});
      if (this.tokens && this.tokens.access_token) headers.set('Authorization', `Bearer ${this.tokens.access_token}`);
      if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
      let response;
      try {
        response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
      } catch (err) {
        const error = new Error('network');
        error.isNetwork = true;
        throw error;
      }
      if (response.status === 401 && this.tokens && this.tokens.refresh_token && !options.skipRefresh) {
        const refreshed = await this.refreshToken().catch(() => null);
        if (refreshed && refreshed.access_token) {
          headers.set('Authorization', `Bearer ${refreshed.access_token}`);
          response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
        }
      }
      const text = await response.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch (_) { data = { message: text.slice(0, 240) || `HTTP ${response.status}` }; }
      if (!response.ok) {
        const message = (data && (data.message || data.detail)) || `HTTP ${response.status}`;
        const error = new Error(typeof message === 'string' ? message : JSON.stringify(message));
        error.status = response.status;
        error.payload = data;
        throw error;
      }
      return data;
    },

    /* ---- 认证 ---- */
    login(account, password) {
      return this.request('/api/auth/login', { method: 'POST', body: JSON.stringify({ login_type: 'password', account, password, device: { platform: 'android-webview' } }) });
    },
    testLogin() { return this.request('/api/auth/test-login', { method: 'POST' }); },
    sendEmailCode(email, purpose) { return this.request('/api/auth/email/send-code', { method: 'POST', body: JSON.stringify({ email, purpose: purpose || 'register' }) }); },
    loginWithEmailCode(email, code) { return this.request('/api/auth/email/login', { method: 'POST', body: JSON.stringify({ email, code }) }); },
    resetPassword(email, emailCode, newPassword) {
      return this.request('/api/auth/reset-password', { method: 'POST', body: JSON.stringify({ email, email_code: emailCode, new_password: newPassword }) });
    },
    register(email, password, displayName, emailCode) {
      return this.request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, display_name: displayName || null, email_code: emailCode || null }) });
    },
    async refreshToken() {
      if (!this.tokens || !this.tokens.refresh_token) throw new Error('No refresh token');
      const refreshed = await this.request('/api/auth/refresh', { method: 'POST', skipRefresh: true, body: JSON.stringify({ refresh_token: this.tokens.refresh_token }) });
      this.setTokens({ ...this.tokens, ...refreshed });
      return refreshed;
    },
    async logout() {
      const refresh = this.tokens && this.tokens.refresh_token;
      try { if (refresh) await this.request('/api/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: refresh }) }); } catch (_) { /* ignore */ }
      this.setTokens(null);
    },

    /* ---- 用户 / 用量 ---- */
    getMe() { return this.request('/api/users/me'); },
    updateMe(payload) { return this.request('/api/users/me', { method: 'PATCH', body: JSON.stringify(payload) }); },
    getUsage() { return this.request('/api/usage/me'); },

    /* ---- 分身 ---- */
    listTwins() { return this.request('/api/twins'); },
    createTwin(payload) { return this.request('/api/twins', { method: 'POST', body: JSON.stringify(payload) }); },
    getTwin(id) { return this.request(`/api/twins/${id}`); },
    updateTwin(id, payload) { return this.request(`/api/twins/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }); },
    deleteTwin(id) { return this.request(`/api/twins/${id}`, { method: 'DELETE' }); },
    syncTwin(id) { return this.request(`/api/twins/${id}/sync`, { method: 'POST', body: '{}' }); },
    getTwinProfile(id) { return this.request(`/api/twins/${id}/profile`); },
    getQuestions(id, mode, limit) { return this.request(`/api/twins/${id}/questions?mode=${encodeURIComponent(mode || 'practice')}&limit=${encodeURIComponent(limit || 12)}`); },
    diagnoseTwin(id, limit) { return this.request(`/api/twins/${id}/diagnose?limit=${encodeURIComponent(limit || 8)}`, { method: 'POST', body: '{}' }); },
    getReviewQueue(id, limit) { return this.request(`/api/twins/${id}/review-queue?limit=${encodeURIComponent(limit || 12)}`); },
    simulateTwin(id) { return this.request(`/api/twins/${id}/simulate`, { method: 'POST', body: '{}' }); },
    createPlan(id) { return this.request(`/api/twins/${id}/plans`, { method: 'POST', body: '{}' }); },
    getPlan(id) { return this.request(`/api/plans/${id}`); },
    updatePlanTask(planId, taskId, payload) { return this.request(`/api/plans/${planId}/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(payload) }); },
    getWeakPoints(id) { return this.request(`/api/twins/${id}/weak-points`); },
    getMemoryMap(id) { return this.request(`/api/twins/${id}/memory-map`); },
    getBlackboard(id, topic) { return this.request(`/api/twins/${id}/blackboard`, { method: 'POST', body: JSON.stringify({ topic: topic || null }) }); },
    synthesizeSpeech(text, voice) { return this.request('/api/speech/tts', { method: 'POST', body: JSON.stringify({ text, voice: voice || null }) }); },
    submitAttempt(payload) { return this.request('/api/attempts', { method: 'POST', body: JSON.stringify(payload) }); },
    listMistakes(twinId, status) { return this.request(`/api/mistakes?twin_id=${encodeURIComponent(twinId)}${status ? `&status=${encodeURIComponent(status)}` : ''}`); },
    createMistake(payload) { return this.request('/api/mistakes', { method: 'POST', body: JSON.stringify(payload) }); },
    updateMistake(id, payload) { return this.request(`/api/mistakes/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }); },
    generateMistakeVariants(id, count) { return this.request(`/api/mistakes/${id}/variants?count=${encodeURIComponent(count || 2)}`, { method: 'POST', body: '{}' }); },

    /* ---- 会话 / 聊天 ---- */
    listConversations(twinId) { return this.request(`/api/conversations${twinId ? `?twin_id=${encodeURIComponent(twinId)}` : ''}`); },
    createConversation(title, twinId) { return this.request('/api/conversations', { method: 'POST', body: JSON.stringify({ title: title || '新对话', twin_id: twinId || null }) }); },
    getConversation(id) { return this.request(`/api/conversations/${id}`); },
    deleteConversation(id) { return this.request(`/api/conversations/${id}`, { method: 'DELETE' }); },
    sendMessage(payload) { return this.request('/api/chat/message', { method: 'POST', body: JSON.stringify(payload) }); },
    async streamMessage(payload, handlers = {}) {
      const headers = new Headers({ 'Content-Type': 'application/json' });
      if (this.tokens && this.tokens.access_token) headers.set('Authorization', `Bearer ${this.tokens.access_token}`);
      const request = () => fetch(`${this.baseUrl}/api/chat/stream`, { method: 'POST', headers, body: JSON.stringify(payload) });
      let response;
      try { response = await request(); }
      catch (err) { const error = new Error('network'); error.isNetwork = true; throw error; }
      if (response.status === 401 && this.tokens && this.tokens.refresh_token) {
        const refreshed = await this.refreshToken().catch(() => null);
        if (refreshed && refreshed.access_token) {
          headers.set('Authorization', `Bearer ${refreshed.access_token}`);
          response = await request();
        }
      }
      if (!response.ok) {
        const text = await response.text();
        let data = null;
        try { data = text ? JSON.parse(text) : null; } catch (_) { data = { message: text.slice(0, 240) }; }
        const message = (data && (data.message || data.detail)) || `HTTP ${response.status}`;
        const error = new Error(typeof message === 'string' ? message : JSON.stringify(message));
        error.status = response.status;
        error.payload = data;
        throw error;
      }
      if (!response.body || !response.body.getReader) {
        const result = await this.sendMessage(payload);
        if (handlers.onStart) handlers.onStart({ conversation_id: result.conversation_id, user_message_id: result.user_message_id });
        if (handlers.onDelta) handlers.onDelta(result.answer || '');
        if (handlers.onDone) handlers.onDone(result);
        return result;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let donePayload = null;
      const dispatch = (block) => {
        const lines = block.split(/\r?\n/);
        let event = 'message';
        const dataLines = [];
        lines.forEach((line) => {
          if (line.startsWith('event:')) event = line.slice(6).trim();
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
        });
        if (!dataLines.length) return;
        let data = {};
        try { data = JSON.parse(dataLines.join('\n')); } catch (_) { data = { raw: dataLines.join('\n') }; }
        if (event === 'start' && handlers.onStart) handlers.onStart(data);
        if (event === 'delta' && handlers.onDelta) handlers.onDelta(data.delta || '');
        if (event === 'done') {
          donePayload = data;
          if (handlers.onDone) handlers.onDone(data);
        }
      };
      while (true) {
        const read = await reader.read();
        if (read.done) break;
        buffer += decoder.decode(read.value, { stream: true });
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() || '';
        parts.forEach(dispatch);
      }
      buffer += decoder.decode();
      if (buffer.trim()) dispatch(buffer);
      return donePayload;
    },

    /* ---- 文件 / 资料 ---- */
    uploadFile(file) { const form = new FormData(); form.append('upload', file); return this.request('/api/files/upload', { method: 'POST', body: form }); },
    listFiles() { return this.request('/api/files'); },
    listDocuments(twinId) { return this.request(`/api/documents${twinId ? `?twin_id=${encodeURIComponent(twinId)}` : ''}`); },
    getDocument(id) { return this.request(`/api/documents/${id}`); },
    parseDocument(fileId, twinId) { return this.request('/api/documents/parse', { method: 'POST', body: JSON.stringify({ file_id: fileId, twin_id: twinId || null }) }); },
  };

  window.DSApi = api;
})();
