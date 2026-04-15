export default function App() {
  useEffect(() => {
    const handleInitialUrl = async () => {
      const initialUrl = await Linking.getInitialURL();
      if (initialUrl) {
        navigateFromUrl(initialUrl);
      }
    };