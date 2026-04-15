function selectModule(url: URL): string | null {
  const requested = url.searchParams.get(MODULE_QUERY_PARAM);
  if (requested !== null) {
    const normalizedRequested = normalizeModulePath(requested);
    if (normalizedRequested === null) {
      return null;
    }
    if (!allowedModules.has(normalizedRequested)) {
      return null;
    }
    return normalizedRequested;
  }