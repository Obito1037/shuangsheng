(function () {
  function normalizeViewportHeight() {
    var vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--app-vh', vh + 'px');
  }

  function updateKeyboardInset() {
    if (!window.visualViewport) {
      document.documentElement.style.setProperty('--keyboard-inset', '0px');
      return;
    }
    var vv = window.visualViewport;
    var keyboardInset = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
    document.documentElement.style.setProperty('--keyboard-inset', keyboardInset + 'px');
  }

  function bindVisualViewport() {
    if (!window.visualViewport) {
      updateKeyboardInset();
      return;
    }
    window.visualViewport.addEventListener('resize', updateKeyboardInset);
    window.visualViewport.addEventListener('scroll', updateKeyboardInset);
    updateKeyboardInset();
  }

  function markLocalStatus() {
    document.documentElement.classList.add('offline-local-assets');
    var hasExternal = Array.prototype.some.call(
      document.querySelectorAll('link[href],script[src]'),
      function (el) {
        var v = el.getAttribute('href') || el.getAttribute('src') || '';
        return /^https?:\/\//i.test(v);
      }
    );
    document.documentElement.classList.toggle('external-resource-left', hasExternal);
    if (hasExternal) {
      console.warn('[DualSheng] External resource remains in index.html.');
    }
  }

  window.addEventListener('resize', function () {
    normalizeViewportHeight();
    updateKeyboardInset();
  });

  window.addEventListener('orientationchange', function () {
    normalizeViewportHeight();
    updateKeyboardInset();
  });

  document.addEventListener('DOMContentLoaded', function () {
    normalizeViewportHeight();
    bindVisualViewport();
    markLocalStatus();
  });
})();
