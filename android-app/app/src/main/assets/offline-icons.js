
(function(){
  var PATHS = {
    add:'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
    arrow_back:'M20 11H7.83l5.59-5.59L12 4 4 12l8 8 1.42-1.41L7.83 13H20v-2z',
    arrow_back_ios_new:'M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12l4.58-4.59z',
    arrow_drop_down:'M7 10l5 5 5-5H7z',
    arrow_upward:'M4 12l1.41 1.41L11 7.83V20h2V7.83l5.59 5.58L20 12 12 4 4 12z',
    camera_alt:'M20 5h-3.17l-1.84-2H9.01L7.17 5H4c-1.1 0-2 .9-2 2v11c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm-8 12.5A4.5 4.5 0 1 1 12 8a4.5 4.5 0 0 1 0 9.5zm0-1.8A2.7 2.7 0 1 0 12 10.3a2.7 2.7 0 0 0 0 5.4z',
    cast_for_education:'M3 5h18v12h-7v2h-4v-2H3V5zm2 2v8h14V7H5zm1 12v2h12v-2H6z',
    chevron_left:'M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12l4.58-4.59z',
    chevron_right:'M8.59 16.59 13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z',
    close:'M18.3 5.71 12 12l6.3 6.29-1.41 1.41L10.59 13.41 4.29 19.71 2.88 18.3 9.17 12 2.88 5.71 4.29 4.3l6.3 6.29 6.29-6.29 1.42 1.41z',
    cloud_upload:'M19.35 10.04A7.49 7.49 0 0 0 5.64 7.11 5.99 5.99 0 0 0 6 19h13a5 5 0 0 0 .35-8.96zM13 13v4h-2v-4H8l4-4 4 4h-3z',
    description:'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13zM8 13h8v2H8v-2zm0 4h8v2H8v-2zm0-8h3v2H8V9z',
    fact_check:'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM8.5 15.5 6 13l1.41-1.41 1.09 1.08 2.59-2.58L12.5 11.6l-4 3.9zM18 14h-5v-2h5v2zm0-4h-5V8h5v2z',
    functions:'M18 4h-2.18l-4.17 12.5L8.34 7H6l4.42 12.5L8.92 24H11.1L15.27 11.5 18.58 21H21L16.58 8.5 18 4z',
    group:'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5s-3 1.34-3 3 1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5C15 14.17 10.33 13 8 13zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z',
    image:'M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 11.5l2.5 3.01L14.5 10l4.5 6H5l3.5-4.5z',
    lock:'M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9a2 2 0 1 1 0-4 2 2 0 0 1 0 4zM9 8V6c0-1.66 1.34-3 3-3s3 1.34 3 3v2H9z',
    memory:'M15 9H9v6h6V9zm-2 4h-2v-2h2v2zm8-2V9h-2V7c0-1.1-.9-2-2-2h-2V3h-2v2h-2V3H9v2H7c-1.1 0-2 .9-2 2v2H3v2h2v2H3v2h2v2c0 1.1.9 2 2 2h2v2h2v-2h2v2h2v-2h2c1.1 0 2-.9 2-2v-2h2v-2h-2v-2h2zM7 17V7h10v10H7z',
    menu:'M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z',
    menu_book:'M21 4.5c-1.11-.35-2.33-.5-3.5-.5-1.95 0-4.05.4-5.5 1.5C10.55 4.4 8.45 4 6.5 4 4.55 4 2.45 4.4 1 5.5v14.65c0 .25.25.5.5.5.1 0 .15-.05.25-.05C3.1 19.95 4.9 19.5 6.5 19.5c1.95 0 4.05.4 5.5 1.5 1.35-.85 3.8-1.5 5.5-1.5 1.65 0 3.35.3 4.75 1.05.1.05.15.05.25.05.25 0 .5-.25.5-.5V5.5c-.6-.45-1.25-.75-2-1zM11 18.5c-1.25-.65-2.9-1-4.5-1-1.25 0-2.45.15-3.5.5V6.6c1.05-.4 2.25-.6 3.5-.6 1.6 0 3.25.35 4.5 1v11.5zm10-.5c-1.05-.35-2.25-.5-3.5-.5-1.6 0-3.25.35-4.5 1V7c1.25-.65 2.9-1 4.5-1 1.25 0 2.45.2 3.5.6V18z',
    mic:'M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.49 6-3.31 6-6.72h-1.7z',
    more_vert:'M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z',
    notifications:'M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4a1.5 1.5 0 0 0-3 0v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z',
    palette:'M12 3C7.03 3 3 6.58 3 11c0 3.31 2.69 6 6 6h1.5c.83 0 1.5.67 1.5 1.5S12.67 20 13.5 20H15c3.31 0 6-2.69 6-6v-1c0-5.52-4.03-10-9-10zM6.5 11C5.67 11 5 10.33 5 9.5S5.67 8 6.5 8 8 8.67 8 9.5 7.33 11 6.5 11zm3-4C8.67 7 8 6.33 8 5.5S8.67 4 9.5 4 11 4.67 11 5.5 10.33 7 9.5 7zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 4 14.5 4 16 4.67 16 5.5 15.33 7 14.5 7zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 8 17.5 8 19 8.67 19 9.5 18.33 11 17.5 11z',
    person:'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z',
    phone_iphone:'M17 1H7c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-2-2-2zm-5 21c-.69 0-1.25-.56-1.25-1.25S11.31 19.5 12 19.5s1.25.56 1.25 1.25S12.69 22 12 22zm5-4H7V4h10v14z',
    picture_as_pdf:'M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM9 11h1.5c.83 0 1.5-.67 1.5-1.5S11.33 8 10.5 8H8v6h1v-3zm0-2h1.5c.28 0 .5.22.5.5s-.22.5-.5.5H9V9zm5 5h-2V8h2c1.1 0 2 .9 2 2v2c0 1.1-.9 2-2 2zm-1-1h1c.55 0 1-.45 1-1v-2c0-.55-.45-1-1-1h-1v4zm7-4h-2v1h2v1h-2v3h-1V8h3v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6z',
    play_arrow:'M8 5v14l11-7L8 5z',
    route:'M19 15.18V7c0-2.21-1.79-4-4-4s-4 1.79-4 4v10c0 1.1-.9 2-2 2s-2-.9-2-2V8.82C8.16 8.4 9 7.3 9 6c0-1.66-1.34-3-3-3S3 4.34 3 6c0 1.3.84 2.4 2 2.82V17c0 2.21 1.79 4 4 4s4-1.79 4-4V7c0-1.1.9-2 2-2s2 .9 2 2v8.18c-1.16.41-2 1.52-2 2.82 0 1.66 1.34 3 3 3s3-1.34 3-3c0-1.3-.84-2.4-2-2.82z',
    search:'M9.5 3a6.5 6.5 0 0 1 5.15 10.46l4.45 4.44-1.41 1.41-4.44-4.45A6.5 6.5 0 1 1 9.5 3zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9z',
    security:'M12 1 3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18 7 3.11V11c0 4.52-2.98 8.69-7 9.93C7.98 19.69 5 15.52 5 11V6.29l7-3.11z',
    settings:'M19.43 12.98c.04-.32.07-.65.07-.98s-.02-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.37-.31-.6-.22l-2.49 1a7.28 7.28 0 0 0-1.69-.98L14.5 2.42C14.47 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.5.42L9.12 5.07c-.61.23-1.18.56-1.69.98l-2.49-1c-.23-.08-.48 0-.6.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.08.65-.08.98s.03.66.08.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.37.31.6.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.38-2.65c.61-.25 1.18-.58 1.69-.98l2.49 1c.23.08.48 0 .6-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5A3.5 3.5 0 1 1 12 8a3.5 3.5 0 0 1 0 7.5z',
    sms:'M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM7 9h10v2H7V9zm0-3h10v2H7V6zm0 6h7v2H7v-2z',
    sync:'M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.96-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm-6 8c0-1.01.25-1.96.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3c-3.31 0-6-2.69-6-6z',
    track_changes:'M19.07 4.93 17.66 6.34A7.93 7.93 0 0 1 20 12h-2a6 6 0 1 0-6 6v2a8 8 0 1 1 7.07-15.07zM12 8a4 4 0 1 0 4 4h-2a2 2 0 1 1-2-2V8zm9.71 5.29-3-3A1 1 0 0 0 17 11v2h-5v2h5v2a1 1 0 0 0 1.71.71l3-3a1 1 0 0 0 0-1.42z',
    upload_file:'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13zm-1 9v-4H9l3-3 3 3h-3v4h-2z',
    verified:'M12 2 15 5.3l4.4-.6.6 4.4L23 12l-3 2.9-.6 4.4-4.4-.6L12 22l-3-3.3-4.4.6-.6-4.4L1 12l3-2.9.6-4.4 4.4.6L12 2zm-1 13.2 6-6-1.4-1.4L11 12.4 8.4 9.8 7 11.2l4 4z',
    verified_user:'M12 1 3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-1 15-4-4 1.41-1.41L11 13.17l5.59-5.58L18 9l-7 7z',
    visibility:'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 12.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
    visibility_off:'M12 6c3.79 0 7.17 2.13 8.82 5.5-.7 1.43-1.82 2.65-3.2 3.56L19 16.44C20.26 15.36 21.27 13.99 22 12c-1.73-4.39-6-7.5-10-7.5-1.55 0-3.02.3-4.36.83l1.53 1.53C10.05 6.31 11 6 12 6zm-9.19-.19L4.1 7.1 6 9c-1.26 1.08-2.27 2.45-3 4 1.73 4.39 6 7.5 10 7.5 1.55 0 3.02-.3 4.36-.83l2.54 2.54 1.29-1.29L4.1 3.81 2.81 5.1zM9.53 12.53l2.94 2.94A2 2 0 0 1 9.53 12.53zm2.84 5.97c-3.79 0-7.17-2.13-8.82-5.5.65-1.33 1.67-2.49 2.94-3.39l1.55 1.55a4 4 0 0 0 5.42 5.42l1.45 1.45c-.82.31-1.67.47-2.54.47z',
    account_circle:'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 4a3 3 0 1 1 0 6 3 3 0 0 1 0-6zm0 14c-2.67 0-5.03-1.34-6.47-3.39C6.58 14.94 9.53 14 12 14s5.42.94 6.47 2.61C17.03 18.66 14.67 20 12 20z',
    school:'M12 3 1 9l11 6 9-4.91V17h2V9L12 3zm0 14-7-3.82v4L12 21l7-3.82v-4L12 17z',
    font_download:'M9.93 13.5h4.14L12 7.98 9.93 13.5zM20 2H8c-1.1 0-2 .9-2 2v3h2V4h12v12h-3v2h3c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 8 1 20h2.4l1.2-3h5.8l1.2 3H14L9 8H6zm-.6 7 2.1-5.25L9.6 15H5.4z'
  };
  function sizeFromClass(el){
    var cls=Array.prototype.slice.call(el.classList||[]).join(' ');
    var m=cls.match(/text-\[(\d+(?:\.\d+)?)px\]/);
    if(m) return parseFloat(m[1]);
    if(cls.indexOf('text-sm')>=0) return 14;
    if(cls.indexOf('text-xs')>=0) return 12;
    if(cls.indexOf('text-lg')>=0) return 18;
    if(cls.indexOf('text-xl')>=0) return 20;
    if(cls.indexOf('text-3xl')>=0) return 30;
    var computed=parseFloat(window.getComputedStyle(el).fontSize);
    return computed && computed > 0 ? computed : 24;
  }
  function replaceIcon(el){
    if(!el) return;
    var name=(el.textContent||'').trim();
    if(!name || name.indexOf('${')===0) return;
    var path=PATHS[name] || 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 5h2v6h-2V7zm0 8h2v2h-2v-2z';
    var size=sizeFromClass(el);
    el.textContent='';
    el.style.setProperty('--local-icon-size', size+'px');
    var svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 24 24');
    svg.setAttribute('aria-hidden','true');
    svg.setAttribute('focusable','false');
    var p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d', path);
    svg.appendChild(p);
    el.appendChild(svg);
    el.classList.add('local-icon-ready');
  }
  function replaceAll(root){
    root = root || document;
    var nodes = root.querySelectorAll ? root.querySelectorAll('.material-symbols-rounded,.material-symbols-outlined') : [];
    for(var i=0;i<nodes.length;i++) replaceIcon(nodes[i]);
    document.documentElement.classList.remove('icons-booting');
    document.documentElement.classList.add('local-icons-ready');
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ replaceAll(document); }); else replaceAll(document);
  var obs = new MutationObserver(function(muts){
    muts.forEach(function(ms){
      if (ms.type === 'characterData' && ms.target.parentElement?.matches('.material-symbols-rounded,.material-symbols-outlined')) {
        replaceIcon(ms.target.parentElement);
      }
      ms.addedNodes.forEach(function(n){
        if(n.nodeType === 1){
          if(n.matches?.('.material-symbols-rounded,.material-symbols-outlined')) replaceIcon(n);
          replaceAll(n);
        } else if (n.nodeType === 3 && n.parentElement?.matches('.material-symbols-rounded,.material-symbols-outlined')) {
          replaceIcon(n.parentElement);
        }
      });
    });
  });
  if(document.documentElement) obs.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
})();
