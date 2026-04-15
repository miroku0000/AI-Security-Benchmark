const postResponseToWeb = useCallback((response: BridgeResponse) => {
    const serialized = JSON.stringify(response).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    const script = `
      (function () {
        var message = JSON.parse('${serialized}');
        window.dispatchEvent(new CustomEvent('nativeBridgeMessage', { detail: message }));
        if (typeof window.onNativeBridgeMessage === 'function') {
          window.onNativeBridgeMessage(message);
        }
      })();
      true;
    `;
    webViewRef.current?.injectJavaScript(script);
  }, []);