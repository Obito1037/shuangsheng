/* 双生 · 认证屏（登录/注册/验证码/找回） */
(function () {
  'use strict';
  const { qs, qsa, esc, toast, toastError, logoSvg, openDoc } = window.DSUi;
  const api = window.DSApi;

  const STATES = {
    login_password: { title: '欢迎回来', subtitle: '试错留给分身，时间留给成长', header: 'tabs', tab: 0 },
    register: { title: '欢迎加入', subtitle: '开始训练一个长期属于你的学习分身', header: 'tabs', tab: 1 },
    login_code: { title: '欢迎回来', subtitle: '试错留给分身，时间留给成长', header: 'sub', sub: '邮箱验证码登录' },
    forgot: { title: '找回密码', subtitle: '当前版本请使用邮箱验证码登录', header: 'sub', sub: '找回密码' },
  };
  let current = 'login_password';
  let codeTimers = {};

  function switchState(next) {
    if (!STATES[next] || next === current) return;
    current = next;
    const cfg = STATES[next];
    qs('#auth-title').textContent = cfg.title;
    qs('#auth-subtitle').textContent = cfg.subtitle;
    qs('#auth-head-tabs').classList.toggle('on', cfg.header === 'tabs');
    qs('#auth-head-sub').classList.toggle('on', cfg.header === 'sub');
    if (cfg.header === 'tabs') {
      qs('#auth-seg').classList.toggle('pos-1', cfg.tab === 1);
      qs('#tab-login').classList.toggle('on', cfg.tab === 0);
      qs('#tab-register').classList.toggle('on', cfg.tab === 1);
    } else {
      qs('#auth-sub-title').textContent = cfg.sub;
    }
    qsa('.auth-panel').forEach((p) => p.classList.remove('on'));
    qs(`#panel-${next}`).classList.add('on');
  }

  function requireTerms() {
    if (qs('#terms-checkbox').checked) return true;
    toast('请先勾选同意用户协议与隐私政策', 'info');
    return false;
  }

  async function withBusy(btn, fn) {
    const original = btn.textContent;
    btn.disabled = true; btn.textContent = '请稍候…';
    try { await fn(); } catch (err) { toastError(err); }
    btn.disabled = false; btn.textContent = original;
  }

  function bindCodeButton(btnId, emailInputId, purpose) {
    const btn = qs(`#${btnId}`);
    btn.addEventListener('click', async () => {
      const email = qs(`#${emailInputId}`).value.trim();
      if (!email || !email.includes('@')) { toast('请输入邮箱地址', 'info'); return; }
      if (codeTimers[btnId]) return;
      btn.disabled = true;
      try {
        await api.sendEmailCode(email, purpose);
        toast('验证码已发送，请查收邮箱', 'ok');
        let left = 60;
        btn.textContent = `${left}s`;
        codeTimers[btnId] = setInterval(() => {
          left -= 1;
          if (left <= 0) { clearInterval(codeTimers[btnId]); codeTimers[btnId] = null; btn.textContent = '获取验证码'; btn.disabled = false; }
          else btn.textContent = `${left}s`;
        }, 1000);
      } catch (err) {
        toastError(err); btn.disabled = false;
      }
    });
  }

  async function finishLogin(result) {
    api.setTokens(result.tokens);
    await window.DSApp.hydrate(result.user);
    window.DSApp.enterApp();
  }

  function html() {
    return `
<div class="auth-wrap hide-scrollbar" style="overflow-y:auto">
  <div class="auth-brand rise rise-1">
    ${logoSvg(84, false)}
    <h1 id="auth-title">欢迎回来</h1>
    <p id="auth-subtitle">试错留给分身，时间留给成长</p>
  </div>

  <div class="auth-card rise rise-2">
    <div class="auth-head">
      <div class="layer on" id="auth-head-tabs">
        <div class="seg" id="auth-seg" style="height:46px">
          <div class="seg-thumb"></div>
          <button id="tab-login" class="on" style="height:38px">登录</button>
          <button id="tab-register" style="height:38px">注册</button>
        </div>
      </div>
      <div class="layer back-row" id="auth-head-sub">
        <button class="icon-btn" data-back-auth><span class="i">arrow_back</span></button>
        <h2 id="auth-sub-title">邮箱验证码登录</h2>
      </div>
    </div>

    <div class="auth-panels">
      <!-- 密码登录 -->
      <form class="auth-panel on" id="panel-login_password">
        <div class="input-shell" style="margin-bottom:12px">
          <span class="i">person</span>
          <input id="lp-account" type="text" placeholder="邮箱" autocomplete="username"/>
        </div>
        <div class="input-shell">
          <span class="i">lock</span>
          <input id="lp-password" type="password" placeholder="密码" autocomplete="current-password"/>
          <button type="button" class="icon-btn suffix-icon" data-eye="lp-password" style="width:36px;height:36px"><span class="i" style="font-size:19px">visibility</span></button>
        </div>
        <div class="auth-links"><a data-goto="forgot">忘记密码？</a></div>
        <button type="submit" class="btn primary block">登录</button>
        <div class="auth-divider">或</div>
        <div class="auth-alt">
          <button type="button" class="btn ghost sm" data-goto="login_code"><span class="i" style="font-size:17px">mail</span>验证码登录</button>
          <button type="button" class="btn ghost sm" id="btn-test-login"><span class="i" style="font-size:17px">bolt</span>体验账号</button>
        </div>
      </form>

      <!-- 注册 -->
      <form class="auth-panel" id="panel-register">
        <div class="input-shell" style="margin-bottom:12px">
          <span class="i">mail</span>
          <input id="rg-email" type="email" placeholder="邮箱" autocomplete="email"/>
        </div>
        <div class="input-shell" style="margin-bottom:12px">
          <span class="i">verified_user</span>
          <input id="rg-code" type="text" placeholder="验证码" style="padding-right:104px"/>
          <button type="button" class="suffix-btn" id="rg-send-code">获取验证码</button>
        </div>
        <div class="input-shell" style="margin-bottom:18px">
          <span class="i">lock</span>
          <input id="rg-password" type="password" placeholder="设置密码（至少 6 位）" autocomplete="new-password"/>
          <button type="button" class="icon-btn suffix-icon" data-eye="rg-password" style="width:36px;height:36px"><span class="i" style="font-size:19px">visibility</span></button>
        </div>
        <button type="submit" class="btn primary block">注册并开始</button>
      </form>

      <!-- 验证码登录 -->
      <form class="auth-panel" id="panel-login_code">
        <div class="input-shell" style="margin-bottom:12px">
          <span class="i">mail</span>
          <input id="lc-email" type="email" placeholder="邮箱"/>
        </div>
        <div class="input-shell" style="margin-bottom:18px">
          <span class="i">verified_user</span>
          <input id="lc-code" type="text" placeholder="验证码" style="padding-right:104px"/>
          <button type="button" class="suffix-btn" id="lc-send-code">获取验证码</button>
        </div>
        <button type="submit" class="btn primary block">登录</button>
      </form>

      <!-- 找回密码 -->
      <form class="auth-panel" id="panel-forgot">
        <div class="input-shell" style="margin-bottom:12px">
          <span class="i">mail</span>
          <input id="fg-email" type="email" placeholder="邮箱" autocomplete="email"/>
        </div>
        <div class="input-shell" style="margin-bottom:12px">
          <span class="i">verified_user</span>
          <input id="fg-code" type="text" placeholder="验证码" style="padding-right:104px"/>
          <button type="button" class="suffix-btn" id="fg-send-code">获取验证码</button>
        </div>
        <div class="input-shell" style="margin-bottom:18px">
          <span class="i">lock</span>
          <input id="fg-password" type="password" placeholder="设置新密码（至少 6 位）" autocomplete="new-password"/>
          <button type="button" class="icon-btn suffix-icon" data-eye="fg-password" style="width:36px;height:36px"><span class="i" style="font-size:19px">visibility</span></button>
        </div>
        <button type="submit" class="btn primary block">重置密码并登录</button>
      </form>
    </div>
  </div>

  <footer class="auth-foot rise rise-3">
    <label class="terms">
      <input type="checkbox" class="checkbox" id="terms-checkbox"/>
      我已阅读并同意
      <a data-doc="agreement">用户协议</a> 与 <a data-doc="policy">隐私政策</a>
    </label>
    <p class="copy">© 2026 双生 Digital Fluency</p>
  </footer>
</div>`;
  }

  function mount(root) {
    root.innerHTML = html();

    qs('#tab-login').addEventListener('click', () => switchState('login_password'));
    qs('#tab-register').addEventListener('click', () => switchState('register'));
    qsa('[data-goto]', root).forEach((n) => n.addEventListener('click', () => switchState(n.getAttribute('data-goto'))));
    qsa('[data-back-auth]', root).forEach((n) => n.addEventListener('click', () => switchState('login_password')));
    qsa('[data-doc]', root).forEach((n) => n.addEventListener('click', (e) => { e.preventDefault(); openDoc(n.getAttribute('data-doc')); }));
    qsa('[data-eye]', root).forEach((n) => n.addEventListener('click', () => {
      const input = qs(`#${n.getAttribute('data-eye')}`);
      const icon = n.querySelector('.i');
      input.type = input.type === 'password' ? 'text' : 'password';
      icon.textContent = input.type === 'password' ? 'visibility' : 'visibility_off';
    }));

    bindCodeButton('rg-send-code', 'rg-email', 'register');
    bindCodeButton('lc-send-code', 'lc-email', 'login');
    bindCodeButton('fg-send-code', 'fg-email', 'reset_password');

    qs('#panel-login_password').addEventListener('submit', (e) => {
      e.preventDefault();
      const account = qs('#lp-account').value.trim();
      const password = qs('#lp-password').value;
      if (!account || !password) { toast('请输入账号和密码', 'info'); return; }
      if (!requireTerms()) return;
      withBusy(e.target.querySelector('button[type=submit]'), async () => {
        await finishLogin(await api.login(account, password));
      });
    });

    qs('#panel-register').addEventListener('submit', (e) => {
      e.preventDefault();
      const email = qs('#rg-email').value.trim();
      const code = qs('#rg-code').value.trim();
      const password = qs('#rg-password').value;
      if (!email || !code || !password) { toast('请输入邮箱、验证码和密码', 'info'); return; }
      if (!requireTerms()) return;
      withBusy(e.target.querySelector('button[type=submit]'), async () => {
        await finishLogin(await api.register(email, password, email.split('@')[0], code));
      });
    });

    qs('#panel-login_code').addEventListener('submit', (e) => {
      e.preventDefault();
      const email = qs('#lc-email').value.trim();
      const code = qs('#lc-code').value.trim();
      if (!email || !code) { toast('请输入邮箱和验证码', 'info'); return; }
      if (!requireTerms()) return;
      withBusy(e.target.querySelector('button[type=submit]'), async () => {
        await finishLogin(await api.loginWithEmailCode(email, code));
      });
    });

    qs('#panel-forgot').addEventListener('submit', (e) => {
      e.preventDefault();
      const email = qs('#fg-email').value.trim();
      const code = qs('#fg-code').value.trim();
      const password = qs('#fg-password').value;
      if (!email || !code || !password) { toast('请输入邮箱、验证码和新密码', 'info'); return; }
      if (!requireTerms()) return;
      withBusy(e.target.querySelector('button[type=submit]'), async () => {
        await finishLogin(await api.resetPassword(email, code, password));
      });
    });

    qs('#btn-test-login').addEventListener('click', (e) => {
      withBusy(e.currentTarget, async () => {
        const result = await api.testLogin();
        await finishLogin(result);
      });
    });
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.auth = { mount, show() { switchState('login_password'); } };
})();
