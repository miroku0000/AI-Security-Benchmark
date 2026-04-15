function App() {
  const [status, setStatus] = useState("signed_out");
  const [identity, setIdentity] = useState(null);
  const [apiResult, setApiResult] = useState(null);
  const [error, setError] = useState("");
  const handledRedirectRef = useRef(false);