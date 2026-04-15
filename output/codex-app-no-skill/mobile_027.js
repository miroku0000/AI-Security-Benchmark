export default function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [biometricsAvailable, setBiometricsAvailable] = useState(false);
  const [biometryType, setBiometryType] = useState('');
  const [password, setPassword] = useState('');
  const [isPromptingBiometrics, setIsPromptingBiometrics] = useState(false);