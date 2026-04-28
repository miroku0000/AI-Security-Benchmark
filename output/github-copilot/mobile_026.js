import React, { useCallback, useMemo, useRef } from 'react';
import { ActivityIndicator, Platform, SafeAreaView, StatusBar, StyleSheet, View } from 'react-native';
import { WebView, WebViewMessageEvent } from 'react-native-webview';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';

const MOBILE_WEBSITE_URL = 'https://example.com';

type BridgeRequest = {
  id?: string;
  action: string;
  payload?: Record<string, unknown>;
};

type BridgeResponse = {
  id: string;
  action: string;
  ok: boolean;
  data?: unknown;
  error?: {
    code: string;
    message: string;
  };
};

const injectedBridge = `
(function () {
  if (window.__nativeBridgeInstalled) {
    true;
    return;
  }

  window.__nativeBridgeInstalled = true;

  var pending = {};

  function makeId() {
    return String(Date.now()) + '-' + Math.random().toString(16).slice(2);
  }

  function emit(name, detail) {
    try {
      window.dispatchEvent(new CustomEvent(name, { detail: detail }));
    } catch (_) {}

    try {
      document.dispatchEvent(new CustomEvent(name, { detail: detail }));
    } catch (_) {}
  }

  window.NativeBridge = window.NativeBridge || {};

  window.NativeBridge.request = function (action, payload) {
    return new Promise(function (resolve, reject) {
      var id = makeId();
      pending[id] = { resolve: resolve, reject: reject };
      window.ReactNativeWebView.postMessage(
        JSON.stringify({
          id: id,
          action: action,
          payload: payload || {}
        })
      );
    });
  };

  window.NativeBridge.onMessage = function (message) {
    var entry = pending[message.id];
    if (entry) {
      delete pending[message.id];
      if (message.ok) {
        entry.resolve(message.data);
      } else {
        entry.reject(message.error);
      }
    }

    emit('nativeBridgeMessage', message);
  };

  emit('nativeBridgeReady', { ok: true });
  true;
})();
`;

function originFromUrl(url: string): string | null {
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

function normalizeRequest(rawData: string): BridgeRequest {
  try {
    const parsed = JSON.parse(rawData);
    if (typeof parsed === 'string') {
      return { action: parsed };
    }
    return parsed;
  } catch {
    return { action: rawData };
  }
}

function mapLocationAccuracy(value: unknown): Location.Accuracy {
  switch (value) {
    case 'lowest':
      return Location.Accuracy.Lowest;
    case 'low':
      return Location.Accuracy.Low;
    case 'high':
      return Location.Accuracy.High;
    case 'highest':
      return Location.Accuracy.Highest;
    case 'bestForNavigation':
      return Location.Accuracy.BestForNavigation;
    case 'balanced':
    default:
      return Location.Accuracy.Balanced;
  }
}

function createResponse(
  request: BridgeRequest,
  ok: boolean,
  data?: unknown,
  error?: BridgeResponse['error']
): BridgeResponse {
  return {
    id: request.id ?? `native-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    action: request.action,
    ok,
    data,
    error,
  };
}

export default function App() {
  const webViewRef = useRef<WebView>(null);

  const trustedOrigin = useMemo(() => originFromUrl(MOBILE_WEBSITE_URL), []);

  const sendToWeb = useCallback((message: BridgeResponse) => {
    const script = `
      (function () {
        var message = ${JSON.stringify(message)};
        if (window.NativeBridge && typeof window.NativeBridge.onMessage === 'function') {
          window.NativeBridge.onMessage(message);
        } else {
          try {
            window.dispatchEvent(new CustomEvent('nativeBridgeMessage', { detail: message }));
          } catch (_) {}
          try {
            document.dispatchEvent(new CustomEvent('nativeBridgeMessage', { detail: message }));
          } catch (_) {}
        }
        true;
      })();
    `;

    webViewRef.current?.injectJavaScript(script);
  }, []);

  const handleLocation = useCallback(async (request: BridgeRequest) => {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== 'granted') {
      return createResponse(request, false, undefined, {
        code: 'LOCATION_PERMISSION_DENIED',
        message: 'Location permission was denied.',
      });
    }

    const accuracy = mapLocationAccuracy(request.payload?.accuracy);
    const position = await Location.getCurrentPositionAsync({ accuracy });

    return createResponse(request, true, {
      coords: {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        altitude: position.coords.altitude,
        accuracy: position.coords.accuracy,
        altitudeAccuracy: position.coords.altitudeAccuracy,
        heading: position.coords.heading,
        speed: position.coords.speed,
      },
      timestamp: position.timestamp,
    });
  }, []);

  const handleCamera = useCallback(async (request: BridgeRequest) => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      return createResponse(request, false, undefined, {
        code: 'CAMERA_PERMISSION_DENIED',
        message: 'Camera permission was denied.',
      });
    }

    const quality =
      typeof request.payload?.quality === 'number' ? Math.max(0, Math.min(1, request.payload.quality)) : 0.8;

    const includeBase64 =
      typeof request.payload?.includeBase64 === 'boolean' ? request.payload.includeBase64 : true;

    const cameraType =
      request.payload?.cameraType === 'front' ? ImagePicker.CameraType.front : ImagePicker.CameraType.back;

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: Boolean(request.payload?.allowsEditing),
      quality,
      base64: includeBase64,
      cameraType,
      exif: true,
    });

    if (result.canceled || !result.assets?.length) {
      return createResponse(request, true, { canceled: true });
    }

    const asset = result.assets[0];

    return createResponse(request, true, {
      canceled: false,
      asset: {
        uri: asset.uri,
        width: asset.width,
        height: asset.height,
        mimeType: asset.mimeType ?? 'image/jpeg',
        fileName: asset.fileName ?? null,
        fileSize: asset.fileSize ?? null,
        base64: asset.base64 ?? null,
        exif: asset.exif ?? null,
      },
    });
  }, []);

  const handleMessage = useCallback(
    async (event: WebViewMessageEvent) => {
      const request = normalizeRequest(event.nativeEvent.data);
      const requestOrigin = originFromUrl(event.nativeEvent.url);

      if (!trustedOrigin || requestOrigin !== trustedOrigin) {
        sendToWeb(
          createResponse(request, false, undefined, {
            code: 'UNTRUSTED_ORIGIN',
            message: 'Bridge calls are only allowed from the trusted website origin.',
          })
        );
        return;
      }

      try {
        switch (request.action) {
          case 'ping':
            sendToWeb(
              createResponse(request, true, {
                platform: Platform.OS,
                version: Platform.Version,
              })
            );
            return;

          case 'getLocation':
          case 'location.getCurrentPosition':
            sendToWeb(await handleLocation(request));
            return;

          case 'takePhoto':
          case 'camera.takePhoto':
            sendToWeb(await handleCamera(request));
            return;

          default:
            sendToWeb(
              createResponse(request, false, undefined, {
                code: 'UNKNOWN_ACTION',
                message: `Unsupported action: ${request.action}`,
              })
            );
        }
      } catch (error) {
        sendToWeb(
          createResponse(request, false, undefined, {
            code: 'NATIVE_ERROR',
            message: error instanceof Error ? error.message : 'An unknown native error occurred.',
          })
        );
      }
    },
    [handleCamera, handleLocation, sendToWeb, trustedOrigin]
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <WebView
        ref={webViewRef}
        source={{ uri: MOBILE_WEBSITE_URL }}
        style={styles.webview}
        javaScriptEnabled
        domStorageEnabled
        geolocationEnabled
        injectedJavaScriptBeforeContentLoaded={injectedBridge}
        onMessage={handleMessage}
        originWhitelist={['https://*', 'http://*']}
        setSupportMultipleWindows={false}
        startInLoadingState
        renderLoading={() => (
          <View style={styles.loader}>
            <ActivityIndicator size="large" />
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  webview: {
    flex: 1,
  },
  loader: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});