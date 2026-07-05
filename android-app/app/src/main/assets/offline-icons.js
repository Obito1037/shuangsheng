(function () {
  const glyphs = {
    menu: '\u2630',
    close: '\u00d7',
    arrow_back: '\u2039',
    arrow_back_ios_new: '\u2039',
    chevron_right: '\u203a',
    chevron_left: '\u2039',
    add: '+',
    more_vert: '\u22ee',
    visibility: '\u25d5',
    visibility_off: '\u25d4',
    account_circle: '\u25ef',
    sms: '\u2709',
    person: '\u25cf',
    lock: '\u25a0',
    verified: '\u2713',
    verified_user: '\u2713',
    description: '\u25a4',
    cloud_upload: '\u21e7',
    upload_file: '\u21e7',
    route: '\u2192',
    cast_for_education: '\u25b6',
    fact_check: '\u2611',
    track_changes: '\u25ce',
    sync: '\u21bb',
    notifications: '\u25cf',
    settings: '\u2699',
    group: '\u25c9',
    school: '\u25b3',
    functions: 'f',
    font_download: 'A',
    picture_as_pdf: 'PDF',
    image: '\u25a7',
    mic: '\u25cf',
    camera_alt: '\u25a3',
    play_arrow: '\u25b6',
    arrow_upward: '\u2191',
    search: '\u2315',
    menu_book: '\u25a4',
    memory: '\u25c7',
    phone_iphone: '\u25af',
    arrow_drop_down: '\u25be'
  };

  function hydrateIcons() {
    document.querySelectorAll('.material-symbols-rounded, .material-symbols-outlined').forEach((node) => {
      const name = (node.getAttribute('data-icon') || node.textContent || '').trim();
      node.setAttribute('data-icon', name);
      if (glyphs[name]) node.textContent = glyphs[name];
    });
  }

  document.addEventListener('DOMContentLoaded', hydrateIcons);
  window.DualShengHydrateIcons = hydrateIcons;
})();
