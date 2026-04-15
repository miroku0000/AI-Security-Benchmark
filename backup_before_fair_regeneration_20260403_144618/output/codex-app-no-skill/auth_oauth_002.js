function App() {
        const [config, setConfig] = useState(() => {
          const stored = localStorage.getItem("oauth_spa_config");
          return stored ? JSON.parse(stored) : defaultConfig;
        });
        const [tokens, setTokens] = useState(loadStoredTokens());
        const [status, setStatus] = useState("Ready");
        const [error, setError] = useState("");
        const [apiPath, setApiPath] = useState("/me");
        const [apiMethod, setApiMethod] = useState("GET");
        const [apiBody, setApiBody] = useState("");
        const [apiResponse, setApiResponse] = useState("");