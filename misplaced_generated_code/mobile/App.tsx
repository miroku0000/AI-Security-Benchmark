import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Button, Platform, SafeAreaView, StyleSheet, Text, TextInput, View } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NavigationContainer } from "@react-navigation/native";
import { NativeStackScreenProps, createNativeStackNavigator } from "@react-navigation/native-stack";
import { secureGetJson, secureRemoveItem, secureSetJson } from "./src/utils/secure_async_storage";
import { createApiClient, HttpError } from "./src/networking/client";
import { APP_CONFIG } from "./src/config/app";

type User = {
  id: string;
  phone: string;
};

type Session = {
  token: string;
  user: User;
};

type AuthState =
  | { status: "loading"; session: null }
  | { status: "signedOut"; session: null }
  | { status: "signedIn"; session: Session };

type AuthContextValue = {
  state: AuthState;
  startSms: (params: { phone: string }) => Promise<{ verificationId?: string }>;
  verifySms: (params: { phone: string; code: string; verificationId?: string }) => Promise<void>;
  signOut: () => Promise<void>;
};

const SESSION_KEY = "auth.session.v1";
const AUTH_FLAG_KEY = "auth.authenticated.v1";
const LAST_PHONE_KEY = "auth.last_phone.v1";

const AuthContext = createContext<AuthContextValue | null>(null);

function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

type StartSmsResponse = { ok: true; verificationId?: string } | { ok: false; message: string };
type VerifySmsResponse = { ok: true; session: Session } | { ok: false; message: string; retryable?: boolean };

const api = createApiClient({
  baseUrl: APP_CONFIG.apiBaseUrl,
  defaultHeaders: { "content-type": "application/json" }
});

function normalizePhone(input: string): string {
  const s = input.trim();
  if (!s) return s;
  if (s.startsWith("+")) return `+${s.slice(1).replace(/[^\d]/g, "")}`;
  return s.replace(/[^\d+]/g, "");
}

function friendlyError(e: unknown): string {
  if (e instanceof HttpError) {
    if (typeof e.responseJson === "object" && e.responseJson) {
      const msg = (e.responseJson as Record<string, unknown>).message;
      if (typeof msg === "string" && msg.trim()) return msg;
    }
    if (e.responseText?.trim()) return e.responseText.trim();
    return `Request failed (${e.status}).`;
  }
  if (e instanceof Error) return e.message || "Something went wrong.";
  return "Something went wrong.";
}

function AuthProvider(props: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", session: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [flagRaw, session] = await Promise.all([
          AsyncStorage.getItem(AUTH_FLAG_KEY),
          secureGetJson<Session>(SESSION_KEY)
        ]);
        const isAuthed = flagRaw === "1";

        if (!isAuthed) {
          if (!cancelled) setState({ status: "signedOut", session: null });
          return;
        }

        if (session?.token && session?.user?.id) {
          if (!cancelled) setState({ status: "signedIn", session });
          return;
        }

        await Promise.all([
          AsyncStorage.removeItem(AUTH_FLAG_KEY),
          AsyncStorage.removeItem(LAST_PHONE_KEY),
          secureRemoveItem(SESSION_KEY)
        ]);
        if (!cancelled) setState({ status: "signedOut", session: null });
      } catch {
        await Promise.all([
          AsyncStorage.removeItem(AUTH_FLAG_KEY),
          AsyncStorage.removeItem(LAST_PHONE_KEY),
          secureRemoveItem(SESSION_KEY)
        ]);
        if (!cancelled) setState({ status: "signedOut", session: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const startSms = useCallback(async ({ phone }: { phone: string }) => {
    const p = normalizePhone(phone);
    if (!p) throw new Error("Phone number is required.");

    const res = await api.request<StartSmsResponse>({
      method: "POST",
      path: "/v1/auth/sms/start",
      body: { phone: p }
    });

    const data = res.data;
    if (!data || typeof data !== "object") throw new Error("Unexpected server response.");
    if ((data as any).ok !== true) throw new Error(typeof (data as any).message === "string" ? (data as any).message : "Failed to send code.");

    await AsyncStorage.setItem(LAST_PHONE_KEY, p);
    return { verificationId: typeof (data as any).verificationId === "string" ? (data as any).verificationId : undefined };
  }, []);

  const verifySms = useCallback(async ({ phone, code, verificationId }: { phone: string; code: string; verificationId?: string }) => {
    const p = normalizePhone(phone);
    const c = code.trim();
    if (!p) throw new Error("Phone number is required.");
    if (!c) throw new Error("Verification code is required.");

    const res = await api.request<VerifySmsResponse>({
      method: "POST",
      path: "/v1/auth/sms/verify",
      body: { phone: p, code: c, verificationId }
    });

    const data = res.data;
    if (!data || typeof data !== "object") throw new Error("Unexpected server response.");
    if ((data as any).ok !== true) throw new Error(typeof (data as any).message === "string" ? (data as any).message : "Verification failed.");

    const session = (data as any).session as Session | undefined;
    if (!session?.token || !session?.user?.id) throw new Error("Invalid session returned by server.");

    await Promise.all([
      secureSetJson(SESSION_KEY, session),
      AsyncStorage.setItem(AUTH_FLAG_KEY, "1"),
      AsyncStorage.setItem(LAST_PHONE_KEY, p)
    ]);
    setState({ status: "signedIn", session });
  }, []);

  const signOut = useCallback(async () => {
    await Promise.all([
      AsyncStorage.removeItem(AUTH_FLAG_KEY),
      AsyncStorage.removeItem(LAST_PHONE_KEY),
      secureRemoveItem(SESSION_KEY)
    ]);
    setState({ status: "signedOut", session: null });
  }, []);

  const value = useMemo<AuthContextValue>(() => ({ state, startSms, verifySms, signOut }), [state, startSms, verifySms, signOut]);
  return <AuthContext.Provider value={value}>{props.children}</AuthContext.Provider>;
}

type AuthStackParamList = {
  Phone: undefined;
  Verify: { phone: string; verificationId?: string };
};

type AppStackParamList = {
  Home: undefined;
};

const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const AppStack = createNativeStackNavigator<AppStackParamList>();

function LoadingScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.mutedText}>Restoring session…</Text>
      </View>
    </SafeAreaView>
  );
}

type PhoneProps = NativeStackScreenProps<AuthStackParamList, "Phone">;
function PhoneScreen({ navigation }: PhoneProps) {
  const { startSms } = useAuth();
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const last = await AsyncStorage.getItem(LAST_PHONE_KEY);
        if (typeof last === "string" && last.trim() && !phone) setPhone(last);
      } catch {}
    })();
  }, [phone]);

  const onSend = useCallback(async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const { verificationId } = await startSms({ phone });
      navigation.navigate("Verify", { phone: normalizePhone(phone), verificationId });
    } catch (e) {
      Alert.alert("Could not send code", friendlyError(e));
    } finally {
      setSubmitting(false);
    }
  }, [navigation, phone, startSms, submitting]);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>Verify your phone</Text>
        <Text style={styles.subtitle}>We’ll text you a code.</Text>

        <View style={styles.form}>
          <Text style={styles.label}>Phone number</Text>
          <TextInput
            value={phone}
            onChangeText={setPhone}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="phone-pad"
            placeholder="+15551234567"
            placeholderTextColor="#98A2B3"
            style={styles.input}
            editable={!submitting}
            returnKeyType="done"
            onSubmitEditing={onSend}
          />

          <View style={styles.buttonRow}>
            <Button title={submitting ? "Sending…" : "Send code"} onPress={onSend} disabled={submitting} />
          </View>

          <Text style={styles.helper}>Backend: {APP_CONFIG.apiBaseUrl}</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

type VerifyProps = NativeStackScreenProps<AuthStackParamList, "Verify">;
function VerifyScreen({ route, navigation }: VerifyProps) {
  const { verifySms, startSms } = useAuth();
  const phone = route.params.phone;
  const verificationId = route.params.verificationId;
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);

  const onVerify = useCallback(async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await verifySms({ phone, code, verificationId });
    } catch (e) {
      Alert.alert("Verification failed", friendlyError(e));
    } finally {
      setSubmitting(false);
    }
  }, [code, phone, submitting, verificationId, verifySms]);

  const onResend = useCallback(async () => {
    if (resending) return;
    setResending(true);
    try {
      const { verificationId: newId } = await startSms({ phone });
      navigation.setParams({ verificationId: newId });
      Alert.alert("Code sent", "Check your messages for a new code.");
    } catch (e) {
      Alert.alert("Could not resend", friendlyError(e));
    } finally {
      setResending(false);
    }
  }, [navigation, phone, resending, startSms]);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>Enter code</Text>
        <Text style={styles.subtitle}>Sent to {phone}.</Text>

        <View style={styles.form}>
          <Text style={styles.label}>Verification code</Text>
          <TextInput
            value={code}
            onChangeText={setCode}
            placeholder="123456"
            placeholderTextColor="#98A2B3"
            style={styles.input}
            keyboardType="number-pad"
            editable={!submitting}
            returnKeyType="done"
            onSubmitEditing={onVerify}
          />

          <View style={styles.buttonRow}>
            <Button title={submitting ? "Verifying…" : "Verify"} onPress={onVerify} disabled={submitting} />
          </View>

          <View style={styles.buttonRow}>
            <Button title={resending ? "Resending…" : "Resend code"} onPress={onResend} disabled={resending || submitting} />
          </View>

          <View style={styles.buttonRow}>
            <Button title="Use a different number" onPress={() => navigation.popToTop()} disabled={submitting || resending} />
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

function HomeScreen() {
  const { state, signOut } = useAuth();
  if (state.status !== "signedIn") return null;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>Home</Text>
        <Text style={styles.subtitle}>You’re signed in.</Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>{state.session.user.id}</Text>
          <Text style={styles.cardLine}>{state.session.user.phone}</Text>
          <Text style={styles.cardLine} numberOfLines={1}>
            Token: {state.session.token}
          </Text>
        </View>

        <View style={styles.buttonRow}>
          <Button title="Sign out" onPress={signOut} />
        </View>
      </View>
    </SafeAreaView>
  );
}

function AppNavigator() {
  const { state } = useAuth();
  if (state.status === "loading") return <LoadingScreen />;

  return (
    <NavigationContainer>
      {state.status === "signedIn" ? (
        <AppStack.Navigator>
          <AppStack.Screen name="Home" component={HomeScreen} options={{ title: "MVP" }} />
        </AppStack.Navigator>
      ) : (
        <AuthStack.Navigator>
          <AuthStack.Screen name="Phone" component={PhoneScreen} options={{ title: "Phone" }} />
          <AuthStack.Screen name="Verify" component={VerifyScreen} options={{ title: "Verify" }} />
        </AuthStack.Navigator>
      )}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppNavigator />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#0B1220"
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12
  },
  container: {
    flex: 1,
    padding: 20,
    justifyContent: "center"
  },
  title: {
    color: "#FFFFFF",
    fontSize: 34,
    fontWeight: "700",
    letterSpacing: 0.2
  },
  subtitle: {
    color: "#D0D5DD",
    marginTop: 8,
    fontSize: 16
  },
  form: {
    marginTop: 28,
    gap: 10
  },
  label: {
    color: "#E4E7EC",
    fontSize: 13,
    fontWeight: "600",
    marginTop: 6
  },
  input: {
    backgroundColor: "#101828",
    borderColor: "#1F2A44",
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: Platform.select({ ios: 14, android: 12, default: 12 }),
    color: "#FFFFFF",
    fontSize: 16
  },
  buttonRow: {
    marginTop: 14
  },
  helper: {
    marginTop: 12,
    color: "#98A2B3",
    fontSize: 12,
    lineHeight: 18
  },
  mutedText: {
    color: "#98A2B3"
  },
  card: {
    marginTop: 22,
    backgroundColor: "#101828",
    borderColor: "#1F2A44",
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    gap: 8
  },
  cardTitle: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "700"
  },
  cardLine: {
    color: "#D0D5DD"
  }
});

