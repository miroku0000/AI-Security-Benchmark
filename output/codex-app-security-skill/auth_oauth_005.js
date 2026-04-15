export default function App() {
  const discovery = AuthSession.useAutoDiscovery(oauthConfig.issuer);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshInFlightRef = useRef(false);
  const appStateRef = useRef<AppStateStatus>(AppState.currentState);