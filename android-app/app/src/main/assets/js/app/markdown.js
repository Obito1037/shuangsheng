/* 双生 · 轻量 Markdown 渲染（无依赖，配合 KaTeX 公式占位） */
(function () {
  'use strict';

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
  }

  // 行内元素：代码、粗体、斜体、行内公式
  function inline(text) {
    let out = escapeHtml(text);
    // 行内公式 $...$ 与 \( \) 先替换为占位 span，交给 KaTeX 后处理
    out = out.replace(/\\\((.+?)\\\)/g, (_, f) => `<span class="math-i" data-f="${escapeHtml(f)}"></span>`);
    out = out.replace(/\$([^$\n]+?)\$/g, (_, f) => `<span class="math-i" data-f="${escapeHtml(f)}"></span>`);
    out = out.replace(/`([^`]+?)`/g, '<code>$1</code>');
    out = out.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/(^|[^*])\*([^*\n]+?)\*/g, '$1<em>$2</em>');
    return out;
  }

  function render(source) {
    const lines = String(source == null ? '' : source).replace(/\r\n/g, '\n').split('\n');
    const html = [];
    let listType = null;   // 'ul' | 'ol'
    let inCode = false;
    let codeBuf = [];
    let inMath = false;
    let mathBuf = [];
    let paraBuf = [];

    function flushPara() {
      if (paraBuf.length) { html.push(`<p>${paraBuf.map(inline).join('<br/>')}</p>`); paraBuf = []; }
    }
    function flushList() {
      if (listType) { html.push(`</${listType}>`); listType = null; }
    }

    for (const raw of lines) {
      const line = raw;

      if (inCode) {
        if (/^\s*```/.test(line)) { html.push(`<pre><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`); codeBuf = []; inCode = false; }
        else codeBuf.push(line);
        continue;
      }
      if (inMath) {
        if (/^\s*(\$\$|\\\])\s*$/.test(line)) {
          html.push(`<div class="math-d" data-f="${escapeHtml(mathBuf.join('\n'))}"></div>`);
          mathBuf = []; inMath = false;
        } else mathBuf.push(line);
        continue;
      }
      if (/^\s*```/.test(line)) { flushPara(); flushList(); inCode = true; continue; }
      if (/^\s*(\$\$|\\\[)\s*$/.test(line)) { flushPara(); flushList(); inMath = true; continue; }
      // 单行 display 公式 $$...$$
      const oneLine = line.match(/^\s*\$\$(.+)\$\$\s*$/);
      if (oneLine) { flushPara(); flushList(); html.push(`<div class="math-d" data-f="${escapeHtml(oneLine[1])}"></div>`); continue; }

      const h = line.match(/^\s*(#{1,3})\s+(.*)$/);
      if (h) { flushPara(); flushList(); html.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); continue; }

      const ul = line.match(/^\s*[-*•]\s+(.*)$/);
      const ol = line.match(/^\s*(\d+)[.、)]\s+(.*)$/);
      if (ul || ol) {
        flushPara();
        const want = ul ? 'ul' : 'ol';
        if (listType !== want) { flushList(); html.push(`<${want}>`); listType = want; }
        html.push(`<li>${inline(ul ? ul[1] : ol[2])}</li>`);
        continue;
      }
      const bq = line.match(/^\s*>\s?(.*)$/);
      if (bq) { flushPara(); flushList(); html.push(`<blockquote>${inline(bq[1])}</blockquote>`); continue; }

      if (!line.trim()) { flushPara(); flushList(); continue; }
      paraBuf.push(line);
    }
    if (inCode && codeBuf.length) html.push(`<pre><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`);
    if (inMath && mathBuf.length) html.push(`<div class="math-d" data-f="${escapeHtml(mathBuf.join('\n'))}"></div>`);
    flushPara(); flushList();
    return html.join('');
  }

  // 把占位符交给 KaTeX（本地 vendor），失败则回退为等宽文本
  function typeset(root) {
    if (!root) return;
    root.querySelectorAll('.math-i, .math-d').forEach((el) => {
      const formula = el.getAttribute('data-f') || '';
      const display = el.classList.contains('math-d');
      if (window.katex && window.katex.render) {
        try {
          window.katex.render(formula, el, { displayMode: display, throwOnError: false });
          return;
        } catch (_) { /* fall through */ }
      }
      el.innerHTML = `<code>${escapeHtml(formula)}</code>`;
    });
  }

  window.DSMarkdown = { render, typeset, escapeHtml };
})();
