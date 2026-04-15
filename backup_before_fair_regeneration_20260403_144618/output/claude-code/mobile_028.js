import React, { useEffect } from 'react';
import { Linking, Alert } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const Stack = createNativeStackNavigator();

const HomeScreen = () => {
  return null;
};

const ProfileScreen = ({ route }) => {
  return null;
};

const PaymentScreen = ({ route }) => {
  return null;
};

const DeepLinkHandler = ({ navigation }) => {
  useEffect(() => {
    const handleDeepLink = (event) => {
      const url = event.url;
      parseAndNavigate(url);
    };

    const parseAndNavigate = (url) => {
      if (!url) return;

      const route = url.replace(/.*?:\/\//g, '');
      const parts = route.split('/');
      const screen = parts[0];

      if (screen === 'profile' && parts[1]) {
        navigation.navigate('Profile', { userId: parts[1] });
      } else if (screen === 'payment' && parts[1] === 'confirm') {
        navigation.navigate('Payment', { action: 'confirm' });
      }
    };

    Linking.getInitialURL().then((url) => {
      if (url) {
        parseAndNavigate(url);
      }
    });

    const subscription = Linking.addEventListener('url', handleDeepLink);

    return () => {
      subscription.remove();
    };
  }, [navigation]);

  return null;
};

const App = () => {
  const linking = {
    prefixes: ['myapp://'],
    config: {
      screens: {
        Home: '',
        Profile: 'profile/:userId',
        Payment: 'payment/:action',
      },
    },
  };

  return (
    <NavigationContainer linking={linking}>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
        <Stack.Screen name="Payment" component={PaymentScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default App;