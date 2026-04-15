import React, { useCallback, useRef } from 'react';
import { View, StyleSheet, Alert, Platform, PermissionsAndroid } from 'react-native';
import { WebView } from 'react-native-webview';

const MOBILE_SITE_URL = 'https://your-mobile-site.example.com';

async function requestCameraPermission() {
  if (Platform.OS !== 'android') {
    return true;
  }

  try {
    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.CAMERA,
      {
        title: 'Camera Permission',
        message: 'This app needs access to your camera.',
        buttonNeutral: 'Ask Me Later',
        buttonNegative: 'Cancel',
        buttonPositive: 'OK',
      }
    );
    return granted === PermissionsAndroid.RESULTS.GRANTED;
  } catch (err) {
    console.warn(err);
    return false;
  }
}

async function requestLocationPermission() {
  if (Platform.OS !== 'android') {
    return true;
  }

  try {
    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      {
        title: 'Location Permission',
        message: 'This app needs access to your location.',
        buttonNeutral: 'Ask Me Later',
        buttonNegative: 'Cancel',
        buttonPositive: 'OK',
      }
    );
    return granted === PermissionsAndroid.RESULTS.GRANTED;
  } catch (err) {
    console.warn(err);
    return false;
  }
}

const MobileWebView = () => {
  const webViewRef = useRef(null);

  const handlePostMessageToWeb = useCallback((data) => {
    if (!webViewRef.current) return;
    webViewRef.current.postMessage(JSON.stringify(data));
  }, []);

  const handleWebMessage = useCallback(
    async (event) => {
      try {
        const data = JSON.parse(event.nativeEvent.data);
        const { type, payload } = data || {};

        switch (type) {
          case 'REQUEST_CAMERA_ACCESS': {
            const granted = await requestCameraPermission();
            if (granted) {
              // TODO: Integrate your camera logic here (e.g., launch camera and return result)
              Alert.alert('Camera Access', 'Camera permission granted.');
              handlePostMessageToWeb({ type: 'CAMERA_PERMISSION_RESULT', granted: true });
            } else {
              Alert.alert('Camera Access', 'Camera permission denied.');
              handlePostMessageToWeb({ type: 'CAMERA_PERMISSION_RESULT', granted: false });
            }
            break;
          }

          case 'REQUEST_LOCATION_ACCESS': {
            const granted = await requestLocationPermission();
            if (granted) {
              // TODO: Integrate your location logic here (e.g., get current location and return)
              Alert.alert('Location Access', 'Location permission granted.');
              handlePostMessageToWeb({
                type: 'LOCATION_PERMISSION_RESULT',
                granted: true,
                // Example placeholder data:
                location: null,
              });
            } else {
              Alert.alert('Location Access', 'Location permission denied.');
              handlePostMessageToWeb({
                type: 'LOCATION_PERMISSION_RESULT',
                granted: false,
              });
            }
            break;
          }

          case 'SHOW_ALERT': {
            const title = payload?.title || 'Message from Web';
            const message = payload?.message || '';
            Alert.alert(title, message);
            break;
          }

          default:
            console.log('Unhandled message from WebView:', data);
        }
      } catch (error) {
        console.warn('Failed to parse message from WebView:', error);
      }
    },
    [handlePostMessageToWeb]
  );

  const injectedJavaScript = `
    (function() {
      // Optional: Expose a helper on window for convenience
      window.nativeBridge = {
        postMessage: function(message) {
          window.ReactNativeWebView.postMessage(JSON.stringify(message));
        },
        requestCameraAccess: function() {
          window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'REQUEST_CAMERA_ACCESS' }));
        },
        requestLocationAccess: function() {
          window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'REQUEST_LOCATION_ACCESS' }));
        },
        showAlert: function(title, message) {
          window.ReactNativeWebView.postMessage(JSON.stringify({
            type: 'SHOW_ALERT',
            payload: { title: title, message: message }
          }));
        }
      };
    })();
    true;
  `;

  return (
    <View style={styles.container}>
      <WebView
        ref={webViewRef}
        source={{ uri: MOBILE_SITE_URL }}
        style={styles.webview}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        injectedJavaScript={injectedJavaScript}
        onMessage={handleWebMessage}
        originWhitelist={['*']}
        allowsInlineMediaPlayback
        mediaPlaybackRequiresUserAction={false}
        startInLoadingState
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  webview: {
    flex: 1,
  },
});

export default MobileWebView;