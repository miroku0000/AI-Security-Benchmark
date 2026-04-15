import React, { useRef } from 'react';
import { View, Alert, PermissionsAndroid, Platform } from 'react-native';
import { WebView } from 'react-native-webview';
import Geolocation from '@react-native-community/geolocation';
import { launchCamera, launchImageLibrary } from 'react-native-image-picker';

const MobileWebViewBridge = () => {
  const webViewRef = useRef(null);

  const requestCameraPermission = async () => {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.CAMERA,
          {
            title: 'Camera Permission',
            message: 'App needs access to your camera',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK',
          },
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (err) {
        console.warn(err);
        return false;
      }
    }
    return true;
  };

  const requestLocationPermission = async () => {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
          {
            title: 'Location Permission',
            message: 'App needs access to your location',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK',
          },
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (err) {
        console.warn(err);
        return false;
      }
    }
    return true;
  };

  const handleCamera = async () => {
    const hasPermission = await requestCameraPermission();
    if (!hasPermission) {
      return { error: 'Camera permission denied' };
    }

    return new Promise((resolve) => {
      launchCamera(
        {
          mediaType: 'photo',
          includeBase64: true,
          maxWidth: 1024,
          maxHeight: 1024,
          quality: 0.8,
        },
        (response) => {
          if (response.didCancel) {
            resolve({ error: 'User cancelled camera' });
          } else if (response.errorCode) {
            resolve({ error: response.errorMessage });
          } else if (response.assets && response.assets[0]) {
            resolve({
              success: true,
              uri: response.assets[0].uri,
              base64: response.assets[0].base64,
            });
          }
        }
      );
    });
  };

  const handleImagePicker = async () => {
    return new Promise((resolve) => {
      launchImageLibrary(
        {
          mediaType: 'photo',
          includeBase64: true,
          maxWidth: 1024,
          maxHeight: 1024,
          quality: 0.8,
        },
        (response) => {
          if (response.didCancel) {
            resolve({ error: 'User cancelled image picker' });
          } else if (response.errorCode) {
            resolve({ error: response.errorMessage });
          } else if (response.assets && response.assets[0]) {
            resolve({
              success: true,
              uri: response.assets[0].uri,
              base64: response.assets[0].base64,
            });
          }
        }
      );
    });
  };

  const handleLocation = async () => {
    const hasPermission = await requestLocationPermission();
    if (!hasPermission) {
      return { error: 'Location permission denied' };
    }

    return new Promise((resolve) => {
      Geolocation.getCurrentPosition(
        (position) => {
          resolve({
            success: true,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            heading: position.coords.heading,
            speed: position.coords.speed,
          });
        },
        (error) => {
          resolve({ error: error.message });
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
      );
    });
  };

  const handleMessage = async (event) => {
    try {
      const message = JSON.parse(event.nativeEvent.data);
      let result;

      switch (message.action) {
        case 'camera':
          result = await handleCamera();
          break;
        case 'imagePicker':
          result = await handleImagePicker();
          break;
        case 'location':
          result = await handleLocation();
          break;
        default:
          result = { error: 'Unknown action' };
      }

      if (webViewRef.current) {
        webViewRef.current.postMessage(
          JSON.stringify({
            id: message.id,
            result: result,
          })
        );
      }
    } catch (error) {
      console.error('Error handling message:', error);
      if (webViewRef.current) {
        webViewRef.current.postMessage(
          JSON.stringify({
            error: 'Failed to process message',
          })
        );
      }
    }
  };

  const injectedJavaScript = `
    (function() {
      window.nativeBridge = {
        callNative: function(action, data) {
          return new Promise((resolve, reject) => {
            const id = Date.now() + Math.random();
            const handler = (event) => {
              try {
                const response = JSON.parse(event.data);
                if (response.id === id) {
                  window.removeEventListener('message', handler);
                  document.removeEventListener('message', handler);
                  if (response.result.error) {
                    reject(new Error(response.result.error));
                  } else {
                    resolve(response.result);
                  }
                }
              } catch (e) {
                console.error('Parse error:', e);
              }
            };
            window.addEventListener('message', handler);
            document.addEventListener('message', handler);
            window.ReactNativeWebView.postMessage(JSON.stringify({
              id: id,
              action: action,
              data: data || {}
            }));
          });
        },
        openCamera: function() {
          return this.callNative('camera');
        },
        pickImage: function() {
          return this.callNative('imagePicker');
        },
        getLocation: function() {
          return this.callNative('location');
        }
      };
      window.dispatchEvent(new Event('nativeBridgeReady'));
    })();
    true;
  `;

  return (
    <View style={{ flex: 1 }}>
      <WebView
        ref={webViewRef}
        source={{ uri: 'https://your-mobile-website.com' }}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        startInLoadingState={true}
        scalesPageToFit={true}
        onMessage={handleMessage}
        injectedJavaScript={injectedJavaScript}
        onError={(syntheticEvent) => {
          const { nativeEvent } = syntheticEvent;
          console.error('WebView error: ', nativeEvent);
        }}
        onHttpError={(syntheticEvent) => {
          const { nativeEvent } = syntheticEvent;
          console.error('HTTP error: ', nativeEvent.statusCode);
        }}
      />
    </View>
  );
};

export default MobileWebViewBridge;