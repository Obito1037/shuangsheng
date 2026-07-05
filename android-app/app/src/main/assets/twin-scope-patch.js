(function () {
  const api = window.DualShengApiClient;
  if (!api || api.__twinScopePatchInstalled) return;
  api.__twinScopePatchInstalled = true;

  function currentTwinId() {
    return window.app?.state?.selectedTwinId || null;
  }

  const rawListConversations = api.listConversations.bind(api);
  api.listConversations = function (twinId) {
    return rawListConversations(twinId || currentTwinId());
  };

  const rawCreateConversation = api.createConversation.bind(api);
  api.createConversation = function (title, twinId) {
    return rawCreateConversation(title, twinId || currentTwinId());
  };

  const rawListDocuments = api.listDocuments.bind(api);
  api.listDocuments = function (twinId) {
    return rawListDocuments(twinId || currentTwinId());
  };

  const rawParseDocument = api.parseDocument.bind(api);
  api.parseDocument = function (fileId, twinId) {
    return rawParseDocument(fileId, twinId || currentTwinId());
  };

  async function reloadSelectedTwinConversations() {
    const app = window.app;
    const appData = window.appData;
    const twinId = currentTwinId();
    if (!app || !appData?.twins?.length || !twinId || !api.tokens?.access_token) return;
    const twin = appData.twins.find((item) => item.id === twinId);
    if (!twin) return;
    try {
      const conversations = await rawListConversations(twinId);
      twin.conversations = (conversations || []).map((item) => ({
        id: item.id,
        title: item.title || '新对话',
        time: item.updated_at ? new Date(item.updated_at).toLocaleDateString() : '刚刚',
        raw: item,
      }));
      if (!twin.conversations.some((item) => item.id === app.state.selectedConversationId)) {
        app.state.selectedConversationId = twin.conversations[0]?.id || null;
      }
      app.renderSidebar?.();
    } catch (error) {
      console.warn('Failed to refresh twin-scoped conversations', error);
    }
  }

  function installAppHooks() {
    const app = window.app;
    if (!app || app.__twinScopeHooksInstalled) return false;
    app.__twinScopeHooksInstalled = true;
    const rawSelectTwin = app.selectTwin?.bind(app);
    if (rawSelectTwin) {
      app.selectTwin = async function (twinId) {
        const result = await rawSelectTwin(twinId);
        await reloadSelectedTwinConversations();
        return result;
      };
    }
    setTimeout(reloadSelectedTwinConversations, 600);
    setTimeout(reloadSelectedTwinConversations, 1500);
    return true;
  }

  const timer = setInterval(() => {
    if (installAppHooks()) clearInterval(timer);
  }, 120);
  setTimeout(() => clearInterval(timer), 5000);
})();
