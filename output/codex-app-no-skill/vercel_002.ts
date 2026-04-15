export default async function handler() {
  const [apiKey, dbUrl, featureFlags] = await Promise.all([
    getValue('API_KEY', DEFAULT_API_KEY),
    getValue('DB_URL', DEFAULT_DB_URL),
    getValue('FEATURE_FLAGS', DEFAULT_FEATURE_FLAGS),
  ]);