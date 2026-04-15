function App() {
        const [config, setConfig] = useState(() => loadJson(CONFIG_KEY, defaultConfig));
        const [tokens, setTokens] = useState(() => loadJson(TOKENS_KEY, null));
        const [profile, setProfile] = useState(() => {
          const stored = loadJson(TOKENS_KEY, null);
          return stored?.id_token ? decodeJwt(stored.id_token) : null;
        });
        const [status, setStatus] = useState({ type: "info", message: "Ready." });
        const [isBusy, setIsBusy] = useState(false);