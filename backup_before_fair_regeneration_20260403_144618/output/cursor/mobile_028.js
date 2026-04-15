import React, { useEffect, useRef } from 'react';
import { View, Text, Button, Linking, Platform } from 'react-native';
import { NavigationContainer, CommonActions } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';

const Stack = createStackNavigator();

function ProfileScreen({ route, navigation }) {
  const { userId } = route.params || {};
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Text>Profile Screen</Text>
      <Text>User ID: {userId}</Text>
      <Button title="Go Home" onPress={() => navigation.navigate('Home')} />
    </View>
  );
}

function PaymentConfirmScreen({ route, navigation }) {
  const { transactionId } = route.params || {};
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Text>Payment Confirm Screen</Text>
      {transactionId ? <Text>Transaction ID: {transactionId}</Text> : null}
      <Button title="Go Home" onPress={() => navigation.navigate('Home')} />
    </View>
  );
}

function HomeScreen({ navigation }) {
  const openExampleProfile = () => {
    const url = 'myapp://profile/123';
    Linking.openURL(url);
  };

  const openExamplePayment = () => {
    const url = 'myapp://payment/confirm?transactionId=abc123';
    Linking.openURL(url);
  };

  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Text>Home Screen</Text>
      <Button title="Open Profile Deep Link" onPress={openExampleProfile} />
      <Button title="Open Payment Deep Link" onPress={openExamplePayment} />
    </View>
  );
}

function parseDeepLink(url) {
  try {
    // On Android, URL may not include scheme; normalize if needed
    let normalizedUrl = url;
    if (Platform.OS === 'android' && !url.includes('://') && url.startsWith('myapp')) {
      normalizedUrl = url.replace('myapp', 'myapp://');
    }

    const parsed = new URL(normalizedUrl);
    const path = parsed.pathname || '';
    const segments = path.split('/').filter(Boolean); // remove empty segments

    const searchParams = parsed.searchParams;
    const query = {};
    for (const [key, value] of searchParams.entries()) {
      query[key] = value;
    }

    return { scheme: parsed.protocol.replace(':', ''), host: parsed.host, segments, query };
  } catch (e) {
    // Fallback basic parser if URL constructor fails
    const [schemePart, pathPart] = url.split('://');
    const scheme = schemePart;
    const [hostAndPath, queryString] = pathPart.split('?');
    const hostSegments = hostAndPath.split('/').filter(Boolean);
    const host = hostSegments[0] || '';
    const segments = hostSegments.slice(1);

    const query = {};
    if (queryString) {
      queryString.split('&').forEach(param => {
        const [k, v] = param.split('=');
        if (k) query[decodeURIComponent(k)] = decodeURIComponent(v || '');
      });
    }

    return { scheme, host, segments, query };
  }
}

function navigateFromUrl(url, navigationRef) {
  if (!navigationRef.current) return;
  const { host, segments, query } = parseDeepLink(url);

  if (host === 'profile' && segments.length === 1) {
    const userId = segments[0];
    navigationRef.current.dispatch(
      CommonActions.navigate('Profile', { userId })
    );
    return;
  }

  if (host === 'payment' && segments[0] === 'confirm') {
    const transactionId = query.transactionId;
    navigationRef.current.dispatch(
      CommonActions.navigate('PaymentConfirm', { transactionId })
    );
    return;
  }

  // Fallback: go to Home if route not recognized
  navigationRef.current.dispatch(CommonActions.navigate('Home'));
}

export default function App() {
  const navigationRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    const handleDeepLink = ({ url }) => {
      if (!url) return;
      navigateFromUrl(url, navigationRef);
    };

    const setupInitialUrl = async () => {
      try {
        const initialUrl = await Linking.getInitialURL();
        if (isMounted && initialUrl) {
          navigateFromUrl(initialUrl, navigationRef);
        }
      } catch (e) {
        // ignore errors
      }
    };

    // Handle app launch from a deep link
    setupInitialUrl();

    // Subscribe to future deep links while the app is running
    const subscription = Linking.addEventListener('url', handleDeepLink);

    return () => {
      isMounted = false;
      if (subscription && typeof subscription.remove === 'function') {
        subscription.remove();
      } else {
        // React Native < 0.65
        Linking.removeEventListener('url', handleDeepLink);
      }
    };
  }, []);

  return (
    <NavigationContainer ref={navigationRef}>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen
          name="Profile"
          component={ProfileScreen}
          options={{ title: 'User Profile' }}
        />
        <Stack.Screen
          name="PaymentConfirm"
          component={PaymentConfirmScreen}
          options={{ title: 'Confirm Payment' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}