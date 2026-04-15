function assertScriptsExist(packageJson, requiredScripts) {
  const scripts = packageJson.scripts || {};
  for (const script of requiredScripts) {
    if (typeof scripts[script] !== 'string' || !scripts[script].trim()) {
      fail(`Missing required package.json script: ${script}`);
    }
  }
}