function buildInjectionScript(response: BridgeResponse): string {
  const serialized = JSON.stringify(response);
  return `
    (function () {
      try {
        var payload = ${serialized};
        var customEventSupported = typeof window.CustomEvent === 'function';
        if (customEventSupported) {
          window.dispatchEvent(new CustomEvent('NativeBridgeMessage', { detail: payload }));
          document.dispatchEvent(new CustomEvent('NativeBridgeMessage', { detail: payload }));
        }
        if (typeof window.MessageEvent === 'function') {
          window.dispatchEvent(new MessageEvent('message', { data: payload }));
          document.dispatchEvent(new MessageEvent('message', { data: payload }));
        }
      } catch (_) {}
    })();
    true;
  `;
}