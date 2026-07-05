(function () {
  const TOKEN_KEY = 'dualsheng.tokens';
  const isAppAssets = location.hostname === 'appassets.androidplatform.net';

  function readTokens() {
    try {
      return JSON.parse(localStorage.getItem(TOKEN_KEY) || 'null');
    } catch (_) {
      return null;
    }
  }

  const client = {
    baseUrl: window.APP_ENV?.BASE_URL || (isAppAssets ? 'https://api.echolearn.cn' : 'http://127.0.0.1:8000'),
    tokens: readTokens(),

    setTokens(tokens) {
      this.tokens = tokens || null;
      if (this.tokens) {
        localStorage.setItem(TOKEN_KEY, JSON.stringify(this.tokens));
      } else {
        localStorage.removeItem(TOKEN_KEY);
      }
    },

    async request(path, options = {}) {
      const headers = new Headers(options.headers || {});
      if (this.tokens?.access_token) {
        headers.set('Authorization', `Bearer ${this.tokens.access_token}`);
      }
      if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }

      let response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
      if (response.status === 401 && this.tokens?.refresh_token && !options.skipRefresh) {
        const refreshed = await this.refreshToken().catch(() => null);
        if (refreshed?.access_token) {
          headers.set('Authorization', `Bearer ${refreshed.access_token}`);
          response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
        }
      }

      const text = await response.text();
      const data = text ? JSON.parse(text) : null;
      if (!response.ok) {
        const message = data?.message || data?.detail || `HTTP ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        error.payload = data;
        throw error;
      }
      return data;
    },

    login(account, password) {
      return this.request('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          login_type: 'password',
          account,
          password,
          device: { platform: 'android-webview' },
        }),
      });
    },

    loginWithEmailCode(email, code) {
      return this.request('/api/auth/email/login', {
        method: 'POST',
        body: JSON.stringify({ email, code }),
      });
    },

    sendEmailCode(email, purpose = 'register') {
      return this.request('/api/auth/email/send-code', {
        method: 'POST',
        body: JSON.stringify({ email, purpose }),
      });
    },

    verifyEmailCode(email, code, purpose = 'register') {
      return this.request('/api/auth/email/verify-code', {
        method: 'POST',
        body: JSON.stringify({ email, purpose, code }),
      });
    },

    register(email, password, displayName, emailCode, verifiedToken) {
      return this.request('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          display_name: displayName || null,
          email_code: emailCode || null,
          verified_token: verifiedToken || null,
        }),
      });
    },

    async refreshToken() {
      if (!this.tokens?.refresh_token) throw new Error('No refresh token');
      const refreshed = await this.request('/api/auth/refresh', {
        method: 'POST',
        skipRefresh: true,
        body: JSON.stringify({ refresh_token: this.tokens.refresh_token }),
      });
      this.setTokens({ ...this.tokens, ...refreshed });
      return refreshed;
    },

    getMe() { return this.request('/api/users/me'); },
    getUsage() { return this.request('/api/usage/me'); },
    listTwins() { return this.request('/api/twins'); },
    createTwin(payload) {
      return this.request('/api/twins', { method: 'POST', body: JSON.stringify(payload) });
    },
    listConversations() { return this.request('/api/conversations'); },
    createConversation(title) {
      return this.request('/api/conversations', {
        method: 'POST',
        body: JSON.stringify({ title: title || '新对话' }),
      });
    },
    getConversation(id) { return this.request(`/api/conversations/${id}`); },
    sendMessage(payload) {
      return this.request('/api/chat/message', { method: 'POST', body: JSON.stringify(payload) });
    },
    uploadFile(file) {
      const form = new FormData();
      form.append('upload', file);
      return this.request('/api/files/upload', { method: 'POST', body: form });
    },
    listFiles() { return this.request('/api/files'); },
    listDocuments() { return this.request('/api/documents'); },
    parseDocument(fileId) {
      return this.request('/api/documents/parse', { method: 'POST', body: JSON.stringify({ file_id: fileId }) });
    },
    simulateTwin(id) { return this.request(`/api/twins/${id}/simulate`, { method: 'POST', body: '{}' }); },
    getWeakPoints(id) { return this.request(`/api/twins/${id}/weak-points`); },
    getBlackboard(id, topic) {
      return this.request(`/api/twins/${id}/blackboard`, {
        method: 'POST',
        body: JSON.stringify({ topic: topic || null }),
      });
    },
  };

  window.DualShengApiClient = client;
})();
