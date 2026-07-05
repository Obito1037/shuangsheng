(function () {
  window.DualShengRuntime = {
    origin: location.origin,
    appassets: location.origin === 'https://appassets.androidplatform.net',
    checkedAt: new Date().toISOString()
  };
  console.log('[DualSheng] runtime', window.DualShengRuntime);
})();
