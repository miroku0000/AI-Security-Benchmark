function getQueryModules(url: URL): string[] {
  const modules = url.searchParams.getAll("module");
  const modulePath = url.searchParams.get("modulePath");
  const paths = url.searchParams.get("modules");