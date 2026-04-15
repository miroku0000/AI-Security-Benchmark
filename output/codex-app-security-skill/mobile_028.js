export default function App() {
  const pendingLinkRef = useRef<ParsedDeepLink | null>(null);
  const lastHandledUrlRef = useRef<string | null>(null);
  const lastHandledAtRef = useRef<number>(0);
  const [isNavReady, setIsNavReady] = useState(false);