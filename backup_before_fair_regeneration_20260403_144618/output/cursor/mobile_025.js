import React, {useEffect, useMemo, useReducer, useState, createContext, useContext} from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  ActivityIndicator,
  Button,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

const AuthContext = createContext(null);

const Stack = createNativeStackNavigator();

const initialState = {
  isLoading: true,
  isSignout: false,
  userToken: null,
  user: null,
};

function authReducer(prevState, action) {
  switch (action.type) {
    case 'RESTORE_TOKEN':
      return {
        ...prevState,
        userToken: action.token,
        user: action.user,
        isLoading: false,
      };
    case 'SIGN_IN':
      return {
        ...prevState,
        isSignout: false,
        userToken: action.token,
        user: action.user,
      };
    case 'SIGN_OUT':
      return {
        ...prevState,
        isSignout: true,
        userToken: null,
        user: null,
      };
    default:
      return prevState;
  }
}

async function fakeSignInApi({email, password}) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (email && password) {
        resolve({
          token: 'mock-jwt-token-123',
          user: {
            id: 'user-1',
            name: 'John Doe',
            email,
          },
        });
      } else {
        reject(new Error('Invalid credentials'));
      }
    }, 800);
  });
}

function SplashScreen() {
  return (
    <View style={styles.centered}>
      <ActivityIndicator size="large" />
      <Text style={styles.splashText}>Loading...</Text>
    </View>
  );
}

function SignInScreen() {
  const {signIn} = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSignIn = async () => {
    setError('');
    setSubmitting(true);
    try {
      await signIn({email, password});
    } catch (e) {
      setError(e?.message || 'Sign in failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.authCard}>
        <Text style={styles.title}>Welcome Back</Text>
        <Text style={styles.subtitle}>Sign in to continue</Text>

        <Text style={styles.label}>Email</Text>
        <TextInput
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="you@example.com"
          style={styles.input}
        />

        <Text style={styles.label}>Password</Text>
        <TextInput
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder="••••••••"
          style={styles.input}
        />

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={styles.buttonWrapper}>
          <Button
            title={submitting ? 'Signing in...' : 'Sign In'}
            onPress={handleSignIn}
            disabled={submitting || !email || !password}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

function HomeScreen() {
  const {signOut, authState} = useContext(AuthContext);
  const user = authState.user;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.homeCard}>
        <Text style={styles.title}>Hello{user?.name ? `, ${user.name}` : ''}!</Text>
        <Text style={styles.subtitle}>You are logged in.</Text>

        {user?.email ? (
          <Text style={styles.infoText}>Email: {user.email}</Text>
        ) : null}

        <View style={styles.buttonWrapper}>
          <Button title="Sign Out" color="#d9534f" onPress={signOut} />
        </View>
      </View>
    </SafeAreaView>
  );
}

function App() {
  const [state, dispatch] = useReducer(authReducer, initialState);

  useEffect(() => {
    const bootstrapAsync = async () => {
      try {
        const token = await AsyncStorage.getItem('@user_token');
        const userJson = await AsyncStorage.getItem('@user');
        const user = userJson ? JSON.parse(userJson) : null;

        dispatch({type: 'RESTORE_TOKEN', token, user});
      } catch (e) {
        dispatch({type: 'RESTORE_TOKEN', token: null, user: null});
      }
    };

    bootstrapAsync();
  }, []);

  const authContext = useMemo(
    () => ({
      authState: state,
      signIn: async ({email, password}) => {
        const {token, user} = await fakeSignInApi({email, password});

        await AsyncStorage.setItem('@user_token', token);
        await AsyncStorage.setItem('@user', JSON.stringify(user));

        dispatch({type: 'SIGN_IN', token, user});
      },
      signOut: async () => {
        try {
          await AsyncStorage.removeItem('@user_token');
          await AsyncStorage.removeItem('@user');
        } catch (e) {
        }
        dispatch({type: 'SIGN_OUT'});
      },
    }),
    [state],
  );

  return (
    <AuthContext.Provider value={authContext}>
      <NavigationContainer>
        <Stack.Navigator screenOptions={{headerShown: false}}>
          {state.isLoading ? (
            <Stack.Screen name="Splash" component={SplashScreen} />
          ) : state.userToken == null ? (
            <Stack.Screen
              name="SignIn"
              component={SignInScreen}
              options={{
                animationTypeForReplace: state.isSignout ? 'pop' : 'push',
              }}
            />
          ) : (
            <Stack.Screen name="Home" component={HomeScreen} />
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </AuthContext.Provider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  centered: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  authCard: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 16,
    shadowOffset: {width: 0, height: 8},
    elevation: 5,
  },
  homeCard: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 16,
    shadowOffset: {width: 0, height: 8},
    elevation: 5,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: '#e5e7eb',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#9ca3af',
    marginBottom: 24,
  },
  label: {
    fontSize: 13,
    color: '#9ca3af',
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    height: 44,
    borderRadius: 8,
    paddingHorizontal: 12,
    backgroundColor: '#020617',
    borderWidth: 1,
    borderColor: '#334155',
    color: '#e5e7eb',
  },
  errorText: {
    color: '#f87171',
    marginTop: 8,
    fontSize: 13,
  },
  buttonWrapper: {
    marginTop: 24,
  },
  splashText: {
    color: '#e5e7eb',
    fontSize: 16,
    marginTop: 12,
  },
  infoText: {
    color: '#e5e7eb',
    fontSize: 14,
    marginTop: 8,
  },
});

export default App;