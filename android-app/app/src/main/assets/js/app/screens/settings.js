/* 双生 · 设置 */
(function () {
  'use strict';

  const { qs, esc, toast, toastError, openDoc, el, subjectMeta, confirmDialog } = window.DSUi;
  const store = window.DSStore;
  const api = window.DSApi;

  const CROP_VIEW = 276;
  const CROP_OUTPUT = 512;
  const MAX_AVATAR_DATA_URL = 300000;

  let root;
  let avatarOverlay = null;
  let nameOverlay = null;
  let cropState = null;

  function activeUserName() {
    const user = store.state.user;
    return (user && user.display_name) || (user && user.email) || '学习者';
  }

  function identityPreview(kind, entity) {
    const isTwin = kind === 'twin';
    const avatar = entity && entity.avatar_data_url ? String(entity.avatar_data_url) : '';
    const label = isTwin ? ((entity && entity.name) || '学习分身') : activeUserName();
    const meta = isTwin ? subjectMeta(entity && entity.subject) : null;
    const fallback = isTwin
      ? `<span class="i" style="--fallback-c1:${meta.c1};--fallback-c2:${meta.c2}">${meta.icon}</span>`
      : `<b>${esc(label.slice(0, 1).toUpperCase())}</b>`;
    return `
<button class="identity-photo ${isTwin ? 'twin' : 'user'}" data-avatar-open="${kind}" type="button" aria-label="${isTwin ? '更改分身头像' : '更改用户头像'}">
  ${avatar ? `<img src="${esc(avatar)}" alt="">` : fallback}
  <span class="identity-edit i">edit</span>
</button>`;
  }

  function render() {
    const user = store.state.user;
    const twin = store.activeTwin();
    const theme = store.state.theme;
    const box = qs('#set-body', root);
    box.innerHTML = `
<div class="page-inner">
  <div class="section-title rise rise-1"><span class="i">account_circle</span>账号资料</div>
  <div class="card set-group identity-card rise rise-1">
    <div class="identity-main">
      ${identityPreview('user', user)}
      <div class="identity-copy">
        <span>用户名</span>
        <b>${esc(activeUserName())}</b>
        <em>${esc(user ? user.email : '')}</em>
      </div>
      <button class="icon-btn edit-float" data-name-open="user" type="button" aria-label="更改用户名"><span class="i">edit</span></button>
    </div>
  </div>

  ${twin ? `
  <div class="section-title rise rise-2"><span class="i">smart_toy</span>当前分身</div>
  <div class="card set-group identity-card rise rise-2">
    <div class="identity-main">
      ${identityPreview('twin', twin)}
      <div class="identity-copy">
        <span>分身名称</span>
        <b>${esc(twin.name)}</b>
        <em>${esc(twin.subject)} · 同步 ${twin.sync_percent || 0}%</em>
      </div>
      <button class="icon-btn edit-float" data-name-open="twin" type="button" aria-label="更改分身名称"><span class="i">edit</span></button>
    </div>
    <button class="set-row" id="set-del-twin" type="button">
      <span class="i" style="color:var(--coral)">delete</span>
      <div class="st-tx"><b style="color:var(--coral)">删除这个分身</b><span>训练数据与会话仍会保留在账号中</span></div>
      <span class="i chev">chevron_right</span>
    </button>
  </div>` : ''}

  <div class="section-title rise rise-3"><span class="i">palette</span>外观</div>
  <div class="card set-group rise rise-3">
    <div class="set-row">
      <span class="i">${theme === 'dark' ? 'dark_mode' : 'light_mode'}</span>
      <div class="st-tx"><b>${theme === 'dark' ? '深色模式' : '浅色模式'}</b></div>
      <div class="seg" style="width:132px" id="set-theme-seg">
        <div class="seg-thumb" style="${theme === 'dark' ? 'transform:translateX(100%)' : ''}"></div>
        <button class="${theme === 'light' ? 'on' : ''}" style="height:32px;font-size:12px">浅色</button>
        <button class="${theme === 'dark' ? 'on' : ''}" style="height:32px;font-size:12px">深色</button>
      </div>
    </div>
  </div>

  <div class="section-title rise rise-4"><span class="i">info</span>关于</div>
  <div class="card set-group rise rise-4">
    <button class="set-row" data-doc="agreement" type="button">
      <span class="i">description</span>
      <div class="st-tx"><b>用户协议</b></div><span class="i chev">chevron_right</span>
    </button>
    <button class="set-row" data-doc="policy" type="button">
      <span class="i">privacy_tip</span>
      <div class="st-tx"><b>隐私政策</b></div><span class="i chev">chevron_right</span>
    </button>
  </div>

  <button class="btn danger block rise rise-5" id="set-logout" type="button" style="margin-top:6px">退出登录</button>
  <p style="text-align:center;font-size:11px;color:var(--ink-3);margin-top:16px">双生 · 试错留给分身，时间留给成长</p>
</div>`;

    bindStaticActions();
  }

  function bindStaticActions() {
    root.querySelectorAll('[data-avatar-open]').forEach((node) => {
      node.addEventListener('click', () => openAvatarOverlay(node.getAttribute('data-avatar-open')));
    });
    root.querySelectorAll('[data-name-open]').forEach((node) => {
      node.addEventListener('click', () => openNameOverlay(node.getAttribute('data-name-open')));
    });
    root.querySelectorAll('[data-doc]').forEach((node) => node.addEventListener('click', () => openDoc(node.getAttribute('data-doc'))));

    const seg = qs('#set-theme-seg', root);
    if (seg) {
      const [lightBtn, darkBtn] = seg.querySelectorAll('button');
      lightBtn.addEventListener('click', () => { window.DSApp.setTheme('light'); render(); });
      darkBtn.addEventListener('click', () => { window.DSApp.setTheme('dark'); render(); });
    }

    const logout = qs('#set-logout', root);
    if (logout) logout.addEventListener('click', async () => {
      await api.logout();
      store.reset();
      window.DSApp.enterAuth();
      toast('已退出登录', 'ok');
    });

    const del = qs('#set-del-twin', root);
    if (del) del.addEventListener('click', async () => {
      const twin = store.activeTwin();
      if (!twin) return;
      const ok = await confirmDialog({
        title: `删除「${twin.name}」？`,
        message: '分身的画像和路线会被移除，账号下的资料与会话仍会保留。',
        okText: '删除',
        icon: 'delete',
      });
      if (!ok) return;
      try {
        await api.deleteTwin(twin.id);
        await window.DSApp.refreshTwins();
        const next = store.state.twins[0];
        window.DSApp.selectTwin(next ? next.id : null, { silent: true });
        toast('分身已删除', 'ok');
        render();
      } catch (err) {
        toastError(err);
      }
    });
  }

  function currentAvatar(target) {
    const entity = target === 'twin' ? store.activeTwin() : store.state.user;
    return entity && entity.avatar_data_url ? String(entity.avatar_data_url) : '';
  }

  function openAvatarOverlay(target) {
    closeNameOverlay();
    closeAvatarOverlay();
    cropState = null;
    avatarOverlay = el(`
<div class="avatar-overlay active" id="settings-avatar-overlay">
  <div class="avatar-sheet card">
    <div class="grip"></div>
    <div class="avatar-sheet-body"></div>
  </div>
</div>`);
    document.body.appendChild(avatarOverlay);
    avatarOverlay.addEventListener('click', (event) => {
      if (event.target === avatarOverlay) closeAvatarOverlay();
    });
    renderAvatarOverlay(target);
  }

  function renderAvatarOverlay(target) {
    if (!avatarOverlay) return;
    const body = qs('.avatar-sheet-body', avatarOverlay);
    const title = target === 'twin' ? '分身头像' : '用户头像';
    const avatar = currentAvatar(target);
    const crop = cropState && cropState.target === target ? cropState : null;
    body.innerHTML = crop ? cropHtml(title, target, crop) : avatarActionsHtml(title, target, avatar);
    bindAvatarOverlay(target);
  }

  function avatarActionsHtml(title, target, avatar) {
    const fallback = target === 'twin'
      ? '<span class="i">smart_toy</span>'
      : `<b>${esc(activeUserName().slice(0, 1).toUpperCase())}</b>`;
    return `
<h3>${esc(title)}</h3>
<div class="sheet-avatar-preview ${target}">
  ${avatar ? `<img src="${esc(avatar)}" alt="">` : fallback}
</div>
<input class="avatar-file-input" id="avatar-file-${target}" type="file" accept="image/*" />
<div class="sheet-action-row">
  <button class="btn ghost block" data-avatar-change type="button"><span class="i">photo_library</span>更改头像</button>
  <button class="btn primary block" data-avatar-save type="button" disabled><span class="i">check</span>保存头像</button>
</div>`;
  }

  function cropHtml(title, target, crop) {
    const zoom = Math.round(crop.zoom * 100);
    return `
<h3>${esc(title)}</h3>
<div class="avatar-crop-wrap">
  <div class="avatar-crop-stage" data-crop-stage>
    <img src="${esc(crop.src)}" alt="" style="${cropImageStyle(crop)}">
    <div class="crop-dim"></div>
    <div class="crop-ring"></div>
  </div>
  <input class="crop-zoom" data-crop-zoom type="range" min="100" max="300" value="${zoom}" />
</div>
<input class="avatar-file-input" id="avatar-file-${target}" type="file" accept="image/*" />
<div class="sheet-action-row">
  <button class="btn ghost block" data-avatar-change type="button"><span class="i">photo_library</span>更改头像</button>
  <button class="btn primary block" data-avatar-save type="button"><span class="i">check</span>保存头像</button>
</div>`;
  }

  function cropImageStyle(crop) {
    return `width:${crop.width}px;height:${crop.height}px;transform:translate(-50%,-50%) translate(${crop.offsetX}px,${crop.offsetY}px) scale(${crop.scale});`;
  }

  function bindAvatarOverlay(target) {
    const file = qs(`#avatar-file-${target}`, avatarOverlay);
    const change = qs('[data-avatar-change]', avatarOverlay);
    const save = qs('[data-avatar-save]', avatarOverlay);
    if (change && file) change.addEventListener('click', () => file.click());
    if (file) file.addEventListener('change', () => chooseAvatarFile(file, target));
    if (save) save.addEventListener('click', () => saveAvatar(target, save));
    const crop = cropState && cropState.target === target ? cropState : null;
    if (crop) bindCropInteractions(target, crop);
  }

  async function chooseAvatarFile(input, target) {
    const file = input.files && input.files[0];
    input.value = '';
    if (!file) return;
    try {
      cropState = await loadCropState(file, target);
      renderAvatarOverlay(target);
    } catch (err) {
      toastError(err);
    }
  }

  function loadCropState(file, target) {
    if (!file.type || !file.type.startsWith('image/')) {
      return Promise.reject(new Error('请选择图片文件'));
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('图片读取失败'));
      reader.onload = () => {
        const img = new Image();
        img.onerror = () => reject(new Error('图片格式暂不支持'));
        img.onload = () => {
          const baseScale = Math.max(CROP_VIEW / img.width, CROP_VIEW / img.height);
          resolve({
            target,
            img,
            src: String(reader.result || ''),
            width: img.width,
            height: img.height,
            baseScale,
            zoom: 1,
            scale: baseScale,
            offsetX: 0,
            offsetY: 0,
          });
        };
        img.src = String(reader.result || '');
      };
      reader.readAsDataURL(file);
    });
  }

  function bindCropInteractions(target, crop) {
    const stage = qs('[data-crop-stage]', avatarOverlay);
    const zoom = qs('[data-crop-zoom]', avatarOverlay);
    const img = stage && stage.querySelector('img');
    if (!stage || !img || !zoom) return;
    const updateImage = () => {
      clampCrop(crop);
      img.style.cssText = cropImageStyle(crop);
    };
    zoom.addEventListener('input', () => {
      crop.zoom = Number(zoom.value || 100) / 100;
      crop.scale = crop.baseScale * crop.zoom;
      updateImage();
    });

    let dragging = false;
    let startX = 0;
    let startY = 0;
    let originX = 0;
    let originY = 0;
    stage.addEventListener('pointerdown', (event) => {
      dragging = true;
      startX = event.clientX;
      startY = event.clientY;
      originX = crop.offsetX;
      originY = crop.offsetY;
      stage.setPointerCapture(event.pointerId);
    });
    stage.addEventListener('pointermove', (event) => {
      if (!dragging) return;
      crop.offsetX = originX + event.clientX - startX;
      crop.offsetY = originY + event.clientY - startY;
      updateImage();
    });
    stage.addEventListener('pointerup', () => { dragging = false; });
    stage.addEventListener('pointercancel', () => { dragging = false; });
  }

  function clampCrop(crop) {
    const maxX = Math.max(0, (crop.width * crop.scale - CROP_VIEW) / 2);
    const maxY = Math.max(0, (crop.height * crop.scale - CROP_VIEW) / 2);
    crop.offsetX = Math.max(-maxX, Math.min(maxX, crop.offsetX));
    crop.offsetY = Math.max(-maxY, Math.min(maxY, crop.offsetY));
  }

  function croppedAvatarDataUrl(crop) {
    clampCrop(crop);
    const canvas = document.createElement('canvas');
    canvas.width = CROP_OUTPUT;
    canvas.height = CROP_OUTPUT;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('当前设备无法处理头像图片');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, CROP_OUTPUT, CROP_OUTPUT);
    ctx.save();
    ctx.beginPath();
    ctx.arc(CROP_OUTPUT / 2, CROP_OUTPUT / 2, CROP_OUTPUT / 2, 0, Math.PI * 2);
    ctx.clip();
    const scale = crop.scale * (CROP_OUTPUT / CROP_VIEW);
    ctx.translate(
      CROP_OUTPUT / 2 + crop.offsetX * (CROP_OUTPUT / CROP_VIEW),
      CROP_OUTPUT / 2 + crop.offsetY * (CROP_OUTPUT / CROP_VIEW),
    );
    ctx.scale(scale, scale);
    ctx.drawImage(crop.img, -crop.width / 2, -crop.height / 2);
    ctx.restore();
    let dataUrl = canvas.toDataURL('image/jpeg', 0.88);
    if (dataUrl.length > MAX_AVATAR_DATA_URL) dataUrl = canvas.toDataURL('image/jpeg', 0.72);
    if (dataUrl.length > MAX_AVATAR_DATA_URL) {
      const small = document.createElement('canvas');
      small.width = 384;
      small.height = 384;
      const smallCtx = small.getContext('2d');
      if (!smallCtx) throw new Error('当前设备无法压缩头像图片');
      smallCtx.drawImage(canvas, 0, 0, 384, 384);
      dataUrl = small.toDataURL('image/jpeg', 0.72);
    }
    if (dataUrl.length > MAX_AVATAR_DATA_URL) throw new Error('头像图片仍然过大，请换一张更小的图片');
    return dataUrl;
  }

  async function saveAvatar(target, button) {
    const crop = cropState && cropState.target === target ? cropState : null;
    if (!crop) return;
    button.disabled = true;
    try {
      const avatarDataUrl = croppedAvatarDataUrl(crop);
      if (target === 'user') {
        const user = store.state.user;
        const updated = await api.updateMe({
          display_name: (user && user.display_name) || activeUserName(),
          avatar_data_url: avatarDataUrl,
        });
        store.set({ user: updated });
      } else {
        const twin = store.activeTwin();
        if (!twin) return;
        const updated = await api.updateTwin(twin.id, { avatar_data_url: avatarDataUrl });
        store.set({ twins: store.state.twins.map((item) => (item.id === updated.id ? updated : item)) });
        invalidateTwinViews();
      }
      toast('头像已更新', 'ok');
      closeAvatarOverlay();
      render();
    } catch (err) {
      toastError(err);
    } finally {
      button.disabled = false;
    }
  }

  function openNameOverlay(target) {
    closeAvatarOverlay();
    closeNameOverlay();
    const isTwin = target === 'twin';
    const twin = store.activeTwin();
    const user = store.state.user;
    const value = isTwin ? ((twin && twin.name) || '') : ((user && user.display_name) || '');
    nameOverlay = el(`
<div class="avatar-overlay active" id="settings-name-overlay">
  <div class="name-sheet card">
    <div class="grip"></div>
    <h3>${isTwin ? '分身名称' : '用户名'}</h3>
    <div class="input-shell no-gap name-edit-input">
      <input class="no-icon" id="settings-name-input" maxlength="120" value="${esc(value)}" />
    </div>
    <button class="btn primary block" id="settings-name-save" type="button"><span class="i">check</span>保存</button>
  </div>
</div>`);
    document.body.appendChild(nameOverlay);
    nameOverlay.addEventListener('click', (event) => {
      if (event.target === nameOverlay) closeNameOverlay();
    });
    const input = qs('#settings-name-input', nameOverlay);
    const save = qs('#settings-name-save', nameOverlay);
    input.focus();
    input.select();
    save.addEventListener('click', () => saveName(target, save));
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') { event.preventDefault(); saveName(target, save); }
    });
  }

  async function saveName(target, button) {
    const input = qs('#settings-name-input', nameOverlay);
    const name = input ? input.value.trim() : '';
    if (!name) { toast('名称不能为空', 'err'); return; }
    button.disabled = true;
    try {
      if (target === 'user') {
        const updated = await api.updateMe({ display_name: name });
        store.set({ user: updated });
      } else {
        const twin = store.activeTwin();
        if (!twin) return;
        const updated = await api.updateTwin(twin.id, { name });
        store.set({ twins: store.state.twins.map((item) => (item.id === updated.id ? updated : item)) });
        invalidateTwinViews();
      }
      toast('已更新', 'ok');
      closeNameOverlay();
      render();
    } catch (err) {
      toastError(err);
    } finally {
      button.disabled = false;
    }
  }

  function invalidateTwinViews() {
    if (window.DSScreens.home && window.DSScreens.home.invalidate) window.DSScreens.home.invalidate();
    if (window.DSScreens.profile && window.DSScreens.profile.invalidate) window.DSScreens.profile.invalidate();
  }

  function closeAvatarOverlay() {
    if (avatarOverlay) avatarOverlay.remove();
    avatarOverlay = null;
    cropState = null;
  }

  function closeNameOverlay() {
    if (nameOverlay) nameOverlay.remove();
    nameOverlay = null;
  }

  function mount(rootEl) {
    root = rootEl;
    root.innerHTML = `
<header class="app-header">
  <button class="icon-btn" id="set-back"><span class="i">arrow_back_ios_new</span></button>
  <div class="title">设置</div>
</header>
<div class="page-body hide-scrollbar" id="set-body"></div>`;
    qs('#set-back', root).addEventListener('click', () => window.DSRouter.back());
  }

  window.DSScreens = window.DSScreens || {};
  window.DSScreens.settings = { mount, show: render };
})();
