function App() {
        const [authState, setAuthState] = useState(() => readAuthState());
        const [errorMessage, setErrorMessage] = useState('');
        const [now, setNow] = useState(Date.now());