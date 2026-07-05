/* 双生 · 共享 UI 工具（toast / sheet / 头像 / 格式化） */
(function () {
  'use strict';

  const esc = window.DSMarkdown.escapeHtml;

  /* ---- DOM ---- */
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }
  function el(html) {
    const tpl = document.createElement('template');
    tpl.innerHTML = html.trim();
    return tpl.content.firstElementChild;
  }

  /* ---- 品牌图形 ---- */
  // 双波浪 logo（沿用原 SVG 造型）
  function logoSvg(size, animated) {
    return `
<svg viewBox="0 0 190 190" xmlns="http://www.w3.org/2000/svg" style="width:${size}px;height:${size}px">
  <defs>
    <linearGradient id="dsg-${size}-${animated ? 'a' : 's'}" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color="#009AFD"/><stop offset="100%" stop-color="#00B2FD"/>
    </linearGradient>
  </defs>
  <rect fill="url(#dsg-${size}-${animated ? 'a' : 's'})" height="190" rx="44" width="190"/>
  <g fill="#FFFFFF">
    <path d="M31 89 L60 49 L95 49 L113 68 L129 49 L159 49 L130 89 L98 89 L75 67 L60 89 Z">
      ${animated ? '<animateTransform attributeName="transform" calcMode="spline" dur="3s" keySplines="0.45 0.05 0.55 0.95; 0.45 0.05 0.55 0.95" repeatCount="indefinite" type="translate" values="0 0; 0 55; 0 0"/>' : ''}
    </path>
    <path d="M31 144 L60 103 L95 103 L113 124 L129 103 L159 103 L130 143 L98 143 L75 122 L60 143 Z">
      ${animated ? '<animateTransform attributeName="transform" calcMode="spline" dur="3s" keySplines="0.45 0.05 0.55 0.95; 0.45 0.05 0.55 0.95" repeatCount="indefinite" type="translate" values="0 0; 0 -55; 0 0"/>' : ''}
    </path>
  </g>
</svg>`;
  }
  // 白色双波浪（用于彩底头像内）
  function markSvg() {
    return `
<svg viewBox="0 0 190 190" xmlns="http://www.w3.org/2000/svg" fill="#FFFFFF">
  <path d="M31 89 L60 49 L95 49 L113 68 L129 49 L159 49 L130 89 L98 89 L75 67 L60 89 Z"/>
  <path d="M31 144 L60 103 L95 103 L113 124 L129 103 L159 103 L130 143 L98 143 L75 122 L60 143 Z"/>
</svg>`;
  }

  const SUBJECT_META = [
    { match: ['数学', 'math'], icon: 'functions', c1: '#009AFD', c2: '#00B2FD' },
    { match: ['英语', 'english'], icon: 'translate', c1: '#2FBF8F', c2: '#0E8A62' },
    { match: ['编程', 'code', 'programming', '计算机'], icon: 'code', c1: '#8F7BF8', c2: '#5F49D8' },
    { match: ['物理', 'physics'], icon: 'rocket_launch', c1: '#F2A03D', c2: '#D97706' },
    { match: ['化学', 'chem'], icon: 'science', c1: '#EE7A94', c2: '#D14D6A' },
  ];
  function subjectMeta(subject) {
    const key = String(subject || '').toLowerCase();
    for (const meta of SUBJECT_META) {
      if (meta.match.some((m) => key.includes(m))) return meta;
    }
    return { icon: 'school', c1: '#009AFD', c2: '#00B2FD' };
  }
  function twinAvatarHtml(twin, sizeCls) {
    const meta = subjectMeta(twin && twin.subject);
    const level = Number((twin && twin.level) || 0);
    const sync = Number((twin && twin.sync_percent) || 0);
    const stage = level >= 8 || sync >= 85 ? 4 : level >= 5 || sync >= 60 ? 3 : level >= 2 || sync >= 30 ? 2 : 1;
    const avatar = twin && twin.avatar_data_url ? String(twin.avatar_data_url) : '';
    if (avatar) {
      return `<div class="twin-avatar image-avatar growth-${stage} ${sizeCls || ''}" style="--av-c1:${meta.c1};--av-c2:${meta.c2}"><img src="${esc(avatar)}" alt=""></div>`;
    }
    return `<div class="twin-avatar growth-${stage} ${sizeCls || ''}" style="--av-c1:${meta.c1};--av-c2:${meta.c2}"><span class="i">${meta.icon}</span></div>`;
  }

  function userAvatarHtml(user, sizeCls) {
    const name = String((user && user.display_name) || (user && user.email) || 'U');
    const avatar = user && user.avatar_data_url ? String(user.avatar_data_url) : '';
    if (avatar) {
      return `<div class="ava user-avatar image-avatar ${sizeCls || ''}"><img src="${esc(avatar)}" alt=""></div>`;
    }
    return `<div class="ava user-avatar ${sizeCls || ''}">${esc(name.slice(0, 1).toUpperCase())}</div>`;
  }

  /* ---- Toast ---- */
  function toast(message, kind) {
    let wrap = qs('#toast-wrap');
    if (!wrap) { wrap = el('<div id="toast-wrap"></div>'); document.body.appendChild(wrap); }
    const icons = { ok: 'check_circle', err: 'error', info: 'info' };
    const node = el(`<div class="toast ${kind || 'info'}"><span class="i fill">${icons[kind] || icons.info}</span><span>${esc(message)}</span></div>`);
    wrap.appendChild(node);
    setTimeout(() => { node.classList.add('out'); setTimeout(() => node.remove(), 300); }, 2600);
  }

  function friendlyError(error) {
    if (!error) return '请求失败，请稍后再试。';
    if (error.isNetwork) return '暂时连不上云端服务，请检查网络后重试。';
    const message = error.message || String(error);
    if (/401|unauthorized|credential|token/i.test(message)) return '登录状态已失效，请重新登录。';
    if (/voice_asr_pending/.test(message)) return '音频已保存，但当前文件还不能直接转写；请使用 16k 单声道 WAV，或先手动填写 transcript。';
    if (/pdf_text_empty/.test(message)) return '这份 PDF 是扫描版，暂时无法提取文字。';
    if (/image_recognition_pending|image_ocr_pending|image_ocr_empty/.test(message)) return '图片已保存，但 OCR / 图像理解暂未识别成功，请稍后重试或换一张更清晰的图片。';
    if (/pdf_parser_missing|pdf_parse_failed/.test(message)) return '该 PDF 解析失败，请换一份试试。';
    return message;
  }
  function toastError(error) { toast(friendlyError(error), 'err'); }

  /* ---- 遮罩 + 抽屉/弹层 ---- */
  function setScrim(on, onTap) {
    let scrim = qs('#global-scrim');
    if (!scrim) {
      scrim = el('<div class="scrim" id="global-scrim"></div>');
      document.body.appendChild(scrim);
    }
    scrim.onclick = onTap || null;
    scrim.classList.toggle('active', Boolean(on));
  }

  /* ---- 文档浮层（协议/隐私） ---- */
  function openDoc(type) {
    const overlay = qs('#overlay-doc');
    if (!overlay) return;
    qsa('.doc-content', overlay).forEach((n) => n.classList.add('hidden'));
    const target = qs(`#doc-${type}`, overlay);
    if (target) target.classList.remove('hidden');
    qs('#overlay-doc-title', overlay).textContent = type === 'agreement' ? '用户协议' : '隐私政策';
    overlay.classList.add('active');
  }
  function closeDoc(agree) {
    const overlay = qs('#overlay-doc');
    if (overlay) overlay.classList.remove('active');
    if (agree) { const cb = qs('#terms-checkbox'); if (cb) cb.checked = true; }
  }

  /* ---- 格式化 ---- */
  function fmtDate(value) {
    if (!value) return '刚刚';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '刚刚';
    const now = new Date();
    const diff = now - d;
    if (diff < 60e3) return '刚刚';
    if (diff < 3600e3) return `${Math.floor(diff / 60e3)} 分钟前`;
    if (d.toDateString() === now.toDateString()) return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return '昨天';
    if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}月${d.getDate()}日`;
    return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
  }
  function fmtSize(bytes) {
    const n = Number(bytes || 0);
    if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB`;
    if (n >= 1024) return `${(n / 1024).toFixed(0)} KB`;
    return `${n} B`;
  }

  /* ---- 文件类型图标 ---- */
  function fileMeta(nameOrType) {
    const s = String(nameOrType || '').toLowerCase();
    if (/\.pdf|application\/pdf/.test(s)) return { icon: 'picture_as_pdf', cls: 'qk-blue' };
    if (/\.(png|jpe?g|webp|bmp)|image\//.test(s)) return { icon: 'image', cls: 'qk-amber' };
    if (/\.(wav|mp3|m4a|aac|flac|ogg)|audio\//.test(s)) return { icon: 'graphic_eq', cls: 'qk-violet' };
    if (/\.(docx?|txt|md)/.test(s)) return { icon: 'description', cls: 'qk-mint' };
    return { icon: 'draft', cls: 'qk-blue' };
  }
  function statusChip(status) {
    const map = {
      parsed: ['已训练', 'mint', 'check_circle'],
      registered: ['待解析', 'amber', 'schedule'],
      parse_pending: ['等待解析', 'amber', 'schedule'],
      parse_failed: ['解析失败', 'coral', 'error'],
      uploaded: ['已上传', 'blue', 'cloud_done'],
    };
    const [label, color, icon] = map[status] || [status || '未知', 'outline', 'help'];
    return `<span class="chip ${color}"><span class="i">${icon}</span>${esc(label)}</span>`;
  }

  /* ---- 打字机（后台/省电模式下 5 秒内兜底完成，不依赖 rAF） ---- */
  function typewriter(node, fullText, done) {
    let idx = 0;
    let finished = false;
    const total = fullText.length;
    const step = Math.max(2, Math.round(total / 90));
    function finish() {
      if (finished) return;
      finished = true;
      node.textContent = fullText;
      if (done) done();
    }
    (function tick() {
      if (finished) return;
      idx = Math.min(total, idx + step);
      node.textContent = fullText.slice(0, idx);
      if (idx < total) setTimeout(tick, 16);
      else finish();
    })();
    setTimeout(finish, 5000);
  }

  window.DSUi = {
    qs, qsa, el, esc,
    logoSvg, markSvg, subjectMeta, twinAvatarHtml, userAvatarHtml,
    toast, toastError, friendlyError,
    setScrim, openDoc, closeDoc,
    fmtDate, fmtSize, fileMeta, statusChip,
    typewriter,
  };
})();
