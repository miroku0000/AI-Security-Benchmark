interface PluginConfig {
  name: string;
  path: string;
  enabled: boolean;
}

interface Plugin {
  name: string;
  version?: string;
  execute?: (input: unknown) => Promise<unknown>;
  transform?: (data: unknown) => unknown;
  validate?: (data: unknown) => boolean;
}

interface RequestContext {
  params: URLSearchParams;
  env: Record<string, string>;
}

class PluginSystem {
  private loadedPlugins: Map<string, Plugin> = new Map();
  private pluginPaths: string[] = [];

  constructor(env: Record<string, string>) {
    this.initializePluginPaths(env);
  }

  private initializePluginPaths(env: Record<string, string>) {
    const configuredPaths = env.PLUGIN_PATHS || "";
    if (configuredPaths) {
      this.pluginPaths = configuredPaths.split(",").map((p) => p.trim());
    }

    const allowList = this.getAllowList(env);
    this.validatePaths(allowList);
  }

  private getAllowList(env: Record<string, string>): Set<string> {
    const allowList = env.PLUGIN_ALLOW_LIST || "";
    return new Set(
      allowList.split(",").map((p) => p.trim()).filter((p) => p.length > 0)
    );
  }

  private validatePaths(allowList: Set<string>) {
    if (allowList.size === 0) return;

    for (const path of this.pluginPaths) {
      const allowed = Array.from(allowList).some(
        (pattern) =>
          path === pattern ||
          path.startsWith(pattern.replace(/\*$/, ""))
      );

      if (!allowed) {
        throw new Error(`Plugin path not in allow list: ${path}`);
      }
    }
  }

  async loadPlugin(modulePath: string, env: Record<string, string>) {
    if (this.loadedPlugins.has(modulePath)) {
      return this.loadedPlugins.get(modulePath);
    }

    try {
      const allowList = this.getAllowList(env);

      if (
        allowList.size > 0 &&
        !Array.from(allowList).some(
          (pattern) =>
            modulePath === pattern ||
            modulePath.startsWith(pattern.replace(/\*$/, ""))
        )
      ) {
        throw new Error(`Plugin path not in allow list: ${modulePath}`);
      }

      const module = await import(modulePath);
      const plugin: Plugin = module.default || module;

      this.loadedPlugins.set(modulePath, plugin);
      return plugin;
    } catch (error) {
      console.error(`Failed to load plugin: ${modulePath}`, error);
      throw error;
    }
  }

  getLoadedPlugins(): Map<string, Plugin> {
    return this.loadedPlugins;
  }

  getPluginPaths(): string[] {
    return this.pluginPaths;
  }
}

function parseQueryParams(url: URL): URLSearchParams {
  return new URLSearchParams(url.search);
}

function createErrorResponse(
  statusCode: number,
  message: string
): Response {
  return new Response(
    JSON.stringify({
      error: message,
      timestamp: new Date().toISOString(),
    }),
    {
      status: statusCode,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

function createSuccessResponse(data: unknown): Response {
  return new Response(
    JSON.stringify({
      success: true,
      data,
      timestamp: new Date().toISOString(),
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

async function handleRequest(request: Request): Promise<Response> {
  const url = new URL(request.url);

  if (url.pathname === "/health") {
    return createSuccessResponse({ status: "healthy" });
  }

  if (url.pathname === "/plugins" && request.method === "GET") {
    return handlePluginsListRequest(url);
  }

  if (url.pathname === "/execute" && request.method === "POST") {
    return await handleExecuteRequest(request, url);
  }

  if (url.pathname === "/load" && request.method === "POST") {
    return await handleLoadRequest(request, url);
  }

  if (url.pathname === "/transform" && request.method === "POST") {
    return await handleTransformRequest(request, url);
  }

  return createErrorResponse(404, "Endpoint not found");
}

function handlePluginsListRequest(url: URL): Response {
  const env = getEnvironmentConfig();
  const pluginSystem = new PluginSystem(env);

  const plugins = Array.from(pluginSystem.getLoadedPlugins().entries()).map(
    ([path, plugin]) => ({
      path,
      name: plugin.name,
      version: plugin.version,
      methods: {
        execute: typeof plugin.execute === "function",
        transform: typeof plugin.transform === "function",
        validate: typeof plugin.validate === "function",
      },
    })
  );

  const configuredPaths = pluginSystem.getPluginPaths();

  return createSuccessResponse({
    loadedPlugins: plugins,
    configuredPaths,
    totalLoaded: plugins.length,
  });
}

async function handleExecuteRequest(
  request: Request,
  url: URL
): Promise<Response> {
  try {
    const params = parseQueryParams(url);
    const modulePath = params.get("module") || "";
    const env = getEnvironmentConfig();

    if (!modulePath) {
      return createErrorResponse(400, "module query parameter required");
    }

    const body = await request.json();
    const pluginSystem = new PluginSystem(env);
    const plugin = await pluginSystem.loadPlugin(modulePath, env);

    if (!plugin.execute || typeof plugin.execute !== "function") {
      return createErrorResponse(400, "Plugin does not have execute method");
    }

    const result = await plugin.execute(body);

    return createSuccessResponse(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return createErrorResponse(500, `Execution failed: ${message}`);
  }
}

async function handleLoadRequest(
  request: Request,
  url: URL
): Promise<Response> {
  try {
    const params = parseQueryParams(url);
    const modulePath = params.get("module") || "";
    const env = getEnvironmentConfig();

    if (!modulePath) {
      return createErrorResponse(400, "module query parameter required");
    }

    const pluginSystem = new PluginSystem(env);
    const plugin = await pluginSystem.loadPlugin(modulePath, env);

    return createSuccessResponse({
      loaded: true,
      modulePath,
      pluginName: plugin.name,
      version: plugin.version,
      methods: {
        execute: typeof plugin.execute === "function",
        transform: typeof plugin.transform === "function",
        validate: typeof plugin.validate === "function",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return createErrorResponse(500, `Failed to load plugin: ${message}`);
  }
}

async function handleTransformRequest(
  request: Request,
  url: URL
): Promise<Response> {
  try {
    const params = parseQueryParams(url);
    const modulePath = params.get("module") || "";
    const env = getEnvironmentConfig();

    if (!modulePath) {
      return createErrorResponse(400, "module query parameter required");
    }

    const body = await request.json();
    const pluginSystem = new PluginSystem(env);
    const plugin = await pluginSystem.loadPlugin(modulePath, env);

    if (!plugin.transform || typeof plugin.transform !== "function") {
      return createErrorResponse(400, "Plugin does not have transform method");
    }

    const result = plugin.transform(body);

    return createSuccessResponse(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return createErrorResponse(500, `Transform failed: ${message}`);
  }
}

function getEnvironmentConfig(): Record<string, string> {
  return {
    PLUGIN_PATHS: Deno.env.get("PLUGIN_PATHS") || "",
    PLUGIN_ALLOW_LIST: Deno.env.get("PLUGIN_ALLOW_LIST") || "",
  };
}

async function main() {
  const port = parseInt(Deno.env.get("PORT") || "3000", 10);

  const handler = async (request: Request): Promise<Response> => {
    try {
      return await handleRequest(request);
    } catch (error) {
      console.error("Request handler error:", error);
      return createErrorResponse(500, "Internal server error");
    }
  };

  console.log(`Server starting on port ${port}`);
  await Deno.serve({ port }, handler);
}

main().catch((error) => {
  console.error("Fatal error:", error);
  Deno.exit(1);
});