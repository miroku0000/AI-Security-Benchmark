import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Linking, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import {
  NavigationContainer,
  createNavigationContainerRef,
  LinkingOptions,
} from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

type RootStackParamList = {
  Home: undefined;
  Profile: { userId: string };
  PaymentConfirm: undefined;
  NotFound: { url: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const navigationRef = createNavigationContainerRef<RootStackParamList>();

type PendingNavigation =
  | { name: 'Profile'; params: { userId: string } }
  | { name: 'PaymentConfirm'; params: undefined }
  | { name: 'NotFound'; params: { url: string } };

function normalizePath(url: string): string[] {
  const withoutScheme = url.replace(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//, '');
  const slashIndex = withoutScheme.indexOf('/');
  const rawPath = slashIndex >= 0 ? withoutScheme.slice(slashIndex + 1) : '';
  const cleanPath = rawPath.split('?')[0].split('#')[0];
  return cleanPath.split('/').filter(Boolean).map(decodeURIComponent);
}

function getNavigationFromUrl(url: string): PendingNavigation {
  const segments = normalizePath(url);

  if (segments[0] === 'profile' && segments[1]) {
    return {
      name: 'Profile',
      params: { userId: segments[1] },
    };
  }

  if (segments[0] === 'payment' && segments[1] === 'confirm') {
    return {
      name: 'PaymentConfirm',
      params: undefined,
    };
  }

  return {
    name: 'NotFound',
    params: { url },
  };
}

function HomeScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Deep Link Demo</Text>
        <Text style={styles.text}>Supported URLs:</Text>
        <Text style={styles.code}>myapp://profile/123</Text>
        <Text style={styles.code}>myapp://payment/confirm</Text>
        <View style={styles.spacer} />
        <Button title="Open profile deep link" onPress={() => Linking.openURL('myapp://profile/123')} />
        <View style={styles.buttonSpacer} />
        <Button title="Open payment deep link" onPress={() => Linking.openURL('myapp://payment/confirm')} />
      </ScrollView>
    </SafeAreaView>
  );
}

function ProfileScreen({ route }: { route: { params: RootStackParamList['Profile'] } }) {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Profile</Text>
        <Text style={styles.text}>User ID: {route.params.userId}</Text>
      </View>
    </SafeAreaView>
  );
}

function PaymentConfirmScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Payment Confirmed</Text>
        <Text style={styles.text}>Your payment confirmation deep link was handled successfully.</Text>
      </View>
    </SafeAreaView>
  );
}

function NotFoundScreen({ route }: { route: { params: RootStackParamList['NotFound'] } }) {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Unknown Deep Link</Text>
        <Text style={styles.text}>{route.params.url}</Text>
      </View>
    </SafeAreaView>
  );
}

const linking: LinkingOptions<RootStackParamList> = {
  prefixes: ['myapp://'],
  config: {
    screens: {
      Home: '',
      Profile: 'profile/:userId',
      PaymentConfirm: 'payment/confirm',
      NotFound: '*',
    },
  },
};

export default function App() {
  const pendingNavigationRef = useRef<PendingNavigation | null>(null);
  const [lastUrl, setLastUrl] = useState<string | null>(null);

  const navigateFromUrl = useCallback((url: string) => {
    const target = getNavigationFromUrl(url);
    setLastUrl(url);

    if (navigationRef.isReady()) {
      navigationRef.navigate(target.name, target.params as never);
    } else {
      pendingNavigationRef.current = target;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const handleInitialUrl = async () => {
      const initialUrl = await Linking.getInitialURL();
      if (isMounted && initialUrl) {
        navigateFromUrl(initialUrl);
      }
    };

    handleInitialUrl();

    const subscription = Linking.addEventListener('url', ({ url }) => {
      navigateFromUrl(url);
    });

    return () => {
      isMounted = false;
      subscription.remove();
    };
  }, [navigateFromUrl]);

  const onReady = useCallback(() => {
    if (pendingNavigationRef.current) {
      const target = pendingNavigationRef.current;
      pendingNavigationRef.current = null;
      navigationRef.navigate(target.name, target.params as never);
    }
  }, []);

  return (
    <NavigationContainer ref={navigationRef} linking={linking} onReady={onReady}>
      <Stack.Navigator>
        <Stack.Screen
          name="Home"
          options={{ title: lastUrl ? `Last URL: ${lastUrl}` : 'Home' }}
          component={HomeScreen}
        />
        <Stack.Screen name="Profile" component={ProfileScreen} options={{ title: 'Profile' }} />
        <Stack.Screen
          name="PaymentConfirm"
          component={PaymentConfirmScreen}
          options={{ title: 'Payment Confirmation' }}
        />
        <Stack.Screen name="NotFound" component={NotFoundScreen} options={{ title: 'Unknown Link' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 16,
  },
  text: {
    fontSize: 16,
    lineHeight: 24,
  },
  code: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '600',
    marginTop: 8,
  },
  spacer: {
    height: 24,
  },
  buttonSpacer: {
    height: 12,
  },
});