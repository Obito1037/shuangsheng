/* 双生 · 资料库（上传 + 训练管线 + 列表） */
(function () {
  'use strict';
  const { qs, esc, toast, toastError, fmtDate, fmtSize, fileMeta, statusChip, friendlyError } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  const ACCEPT = '.pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.bmp,.wav,.mp3,.m4a';
  let root;
  let filter = 'all';
  let loading = false;

  function kindOf(doc) {
    const s = `${doc.content_type || ''} ${doc.title || doc.original_name || ''}`.toLowerCase();
    if (/image|\.(png|jpe?g|webp|bmp)/.test(s)) return 'image';
    if (/audio|\.(wav|mp3|m4a|aac|flac|ogg)/.test(s)) return 'audio';
    return 'doc';
  }

  function queueHtml() {
    const queue = store.state.uploadQueue;
    if (!queue.length) return '';
    const stateChip = {
      uploading: '<span class="chip blue"><span class="i">cloud_upload</span>上传中</span>',
      parsing: '<span class="chip amber"><span class="i">autorenew</span>解析中</span>',
      done: '<span class="chip mint"><span class="i">check_circle</span>已训练</span>',
      failed: '<span class="chip coral"><span class="i">error</span>失败</span>',
    };
    return `
<div class="section-title"><span class="i">upload</span>本次上传</div>
${queue.map((item) => {
  const meta = fileMeta(item.name);
  return `
<div class="card upq-item">
  <div class="uq-ic ${meta.cls}"><span class="i">${meta.icon}</span></div>
  <div class="uq-tx"><b>${esc(item.name)}</b><span>${esc(item.note || '')}</span></div>
  <div class="uq-state">${stateChip[item.state] || ''}</div>
</div>`;
}).join('')}`;
  }

  function docsHtml() {
    const docs = store.state.documents.filter((d) => filter === 'all' || kindOf(d) === filter);
    if (loading) {
      return `<div class="card pad"><div class="skel" style="height:20px;width:60%;margin-bottom:12px"></div>
        <div class="skel" style="height:14px;width:40%"></div></div>
        <div style="height:10px"></div>
        <div class="card pad"><div class="skel" style="height:20px;width:70%;margin-bottom:12px"></div>
        <div class="skel" style="height:14px;width:35%"></div></div>`;
    }
    if (!docs.length) {
      return `<div class="card"><div class="empty-box">
        <span class="i">folder_open</span>
        <h4>${filter === 'all' ? '资料库还是空的' : '这个分类下暂无资料'}</h4>
        <p>上传教材、笔记、错题或课件，<br/>分身会解析并记入自己的知识库。</p>
      </div></div>`;
    }
    return docs.map((doc) => {
      const meta = fileMeta(`${doc.content_type || ''} ${doc.title || ''}`);
      return `
<div class="card doc-item tappable">
  <div class="dc-ic ${meta.cls}"><span class="i">${meta.icon}</span></div>
  <div class="dc-tx">
    <b>${esc(doc.title || doc.original_name || '学习资料')}</b>
    <div class="dc-meta">
      ${statusChip(doc.status || doc.parse_status)}
      <span>${fmtDate(doc.created_at)}</span>
      ${doc.size_bytes ? `<span>${fmtSize(doc.size_bytes)}</span>` : ''}
    </div>
  </div>
</div>`;
    }).join('');
  }

  function render() {
    const listBox = qs('#lib-list', root);
    if (listBox) listBox.innerHTML = queueHtml() + `
<div class="section-title"><span class="i">auto_stories</span>已训练资料
  <span class="spacer"></span>
  <button class="link" id="lib-refresh">刷新</button>
</div>` + docsHtml();
    const refresh = qs('#lib-refresh', root);
    if (refresh) refresh.onclick = () => load(true);
  }

  async function load(force) {
    const twin = store.activeTwin();
    if (!twin) return;
    if (loading && !force) return;
    loading = true; render();
    try {
      const docs = await api.listDocuments(twin.id);
      store.set({ documents: docs || [] });
    } catch (err) { toastError(err); }
    loading = false; render();
  }

  async function handleFiles(files) {
    const twin = store.activeTwin();
    if (!twin) { toast('请先创建学习分身', 'info'); return; }
    if (!files.length) return;
    const queue = files.map((f) => ({ name: f.name, state: 'uploading', note: fmtSize(f.size), file: f }));
    store.set({ uploadQueue: queue });
    render();
    for (const item of queue) {
      try {
        const uploaded = await api.uploadFile(item.file);
        const fileId = (uploaded && uploaded.file && uploaded.file.id) || uploaded.id;
        item.state = 'parsing'; item.note = '正在解析并训练分身…'; render();
        try {
          await api.parseDocument(fileId, twin.id);
          item.state = 'done'; item.note = '已进入分身知识库';
        } catch (parseErr) {
          item.state = 'failed'; item.note = friendlyError(parseErr);
        }
      } catch (err) {
        item.state = 'failed'; item.note = friendlyError(err);
      }
      render();
    }
    await load(true);
    await window.DSApp.refreshTwins();
    const done = queue.filter((q) => q.state === 'done').length;
    if (done) toast(`已训练 ${done} 份资料`, 'ok');
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="lib-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">训练资料库</div>
  <button class="icon-btn primary" id="lib-add"><span class="i">add</span></button>
</header>
<div class="page-body hide-scrollbar">
  <div class="page-inner">
    <button class="upload-zone rise rise-1" id="lib-zone" style="width:100%;margin-bottom:18px">
      <div class="uz-ic"><span class="i">upload_file</span></div>
      <h3>上传资料，训练分身</h3>
      <p>支持 PDF / Word / 文本 / Markdown / 图片（OCR + 图像理解）<br/>音频会先缓存，短语音识别需要 16k 单声道 WAV</p>
      <span class="btn soft sm" style="pointer-events:none"><span class="i" style="font-size:16px">attach_file</span>选择文件</span>
    </button>
    <div class="filter-row hide-scrollbar rise rise-2">
      <button class="chip on" data-filter="all">全部</button>
      <button class="chip" data-filter="doc">文档笔记</button>
      <button class="chip" data-filter="image">图片</button>
      <button class="chip" data-filter="audio">音频</button>
    </div>
    <div id="lib-list"></div>
    <div style="height:30px"></div>
  </div>
</div>`;

    qs('#lib-back', root).addEventListener('click', () => window.DSRouter.back());
    const pick = () => {
      const input = qs('#global-file-input');
      input.accept = ACCEPT;
      input.onchange = (e) => {
        const files = Array.from(e.target.files || []);
        input.value = '';
        handleFiles(files);
      };
      input.click();
    };
    qs('#lib-zone', root).addEventListener('click', pick);
    qs('#lib-add', root).addEventListener('click', pick);
    root.querySelectorAll('[data-filter]').forEach((chip) => {
      chip.addEventListener('click', () => {
        filter = chip.getAttribute('data-filter');
        root.querySelectorAll('[data-filter]').forEach((c) => c.classList.toggle('on', c === chip));
        render();
      });
    });
  }

  function show() { load(true); }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.library = { mount, show };
})();
