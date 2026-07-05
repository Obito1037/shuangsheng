/* 双生 · 新建分身 */
(function () {
  'use strict';
  const { qs, qsa, toast, toastError } = window.DSUi;
  const api = window.DSApi;

  let root;
  let subject = '';

  const SUBJECTS = [
    ['数学', 'functions'], ['英语', 'translate'], ['编程', 'code'],
    ['物理', 'rocket_launch'], ['化学', 'science'], ['综合', 'school'],
  ];

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="tn-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">新建学习分身</div>
</header>
<div class="page-body hide-scrollbar">
  <div class="page-inner">
    <div class="card pad rise rise-1" style="margin-bottom:16px">
      <div class="section-title" style="margin-top:0"><span class="i">badge</span>基本信息</div>
      <div class="field">
        <label>分身名称</label>
        <div class="input-shell"><input id="tn-name" class="no-icon" type="text" placeholder="例如：考研数学分身"/></div>
      </div>
      <div class="field">
        <label>学习方向</label>
        <div class="subject-grid" id="tn-subjects">
          ${SUBJECTS.map(([name, icon]) => `
          <button type="button" class="subject-cell" data-subject="${name}">
            <span class="i">${icon}</span><span>${name}</span>
          </button>`).join('')}
        </div>
        <div class="input-shell" style="margin-top:10px">
          <span class="i">edit</span>
          <input id="tn-subject-custom" type="text" placeholder="或输入其他方向…"/>
        </div>
      </div>
      <div class="field" style="margin-bottom:2px">
        <label>学习目标</label>
        <textarea id="tn-goal" class="area" placeholder="描述你希望这个分身帮你达成什么，例如：三个月内把高数薄弱章节补齐，期末冲 90 分"></textarea>
      </div>
    </div>

    <div class="card pad rise rise-2" style="margin-bottom:20px;background:var(--primary-soft);border-color:transparent">
      <div style="display:flex;gap:10px;align-items:flex-start">
        <span class="i" style="color:var(--primary);font-size:20px;flex-shrink:0;margin-top:2px">tips_and_updates</span>
        <p style="margin:0;font-size:var(--fs-sm);color:var(--primary-ink);line-height:1.7">
          创建后，上传资料、记录错题、日常对话都会持续训练这个分身。方向和目标之后可以随时修改。
        </p>
      </div>
    </div>

    <button class="btn primary block rise rise-3" id="tn-submit"><span class="i">smart_toy</span>创建并开始训练</button>
  </div>
</div>`;

    qs('#tn-back', root).addEventListener('click', () => window.DSRouter.back());
    qsa('[data-subject]', root).forEach((cell) => {
      cell.addEventListener('click', () => {
        subject = cell.getAttribute('data-subject');
        qs('#tn-subject-custom', root).value = '';
        qsa('[data-subject]', root).forEach((c) => c.classList.toggle('on', c === cell));
      });
    });
    qs('#tn-subject-custom', root).addEventListener('input', (e) => {
      if (e.target.value.trim()) {
        subject = '';
        qsa('[data-subject]', root).forEach((c) => c.classList.remove('on'));
      }
    });

    qs('#tn-submit', root).addEventListener('click', async () => {
      const name = qs('#tn-name', root).value.trim();
      const custom = qs('#tn-subject-custom', root).value.trim();
      const finalSubject = custom || subject;
      const goal = qs('#tn-goal', root).value.trim();
      if (!finalSubject) { toast('请选择或输入学习方向', 'info'); return; }
      const btn = qs('#tn-submit', root);
      btn.disabled = true;
      try {
        const twin = await api.createTwin({
          name: name || `${finalSubject}学习分身`,
          subject: finalSubject,
          goal: goal || '持续训练，生成最适合我的学习路径',
        });
        await window.DSApp.refreshTwins();
        window.DSApp.selectTwin(twin.id, { silent: true });
        toast('学习分身已创建', 'ok');
        window.DSRouter.go('home');
      } catch (err) { toastError(err); }
      btn.disabled = false;
    });
  }

  function show() {
    subject = '';
    qsa('[data-subject]', root).forEach((c) => c.classList.remove('on'));
    qs('#tn-name', root).value = '';
    qs('#tn-subject-custom', root).value = '';
    qs('#tn-goal', root).value = '';
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens['twin-new'] = { mount, show };
})();
