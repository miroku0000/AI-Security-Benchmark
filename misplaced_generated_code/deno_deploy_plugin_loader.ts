// @deno-types="https://deno.land/x/hono@v3.12.0/mod.ts"
import { Hono } from "https://deno.land/x/hono@v3.12.0/mod.ts";

interface PluginModule {
  name: string;
  version: string;
  init?: (app: Hono) => void;
  process?: (data: any) => any;
  cleanup?: () => void;
}

interface LoadedPlugin {
  module: PluginModule;
  path: string;
  loadedAt: number;
}

const app = new Hono();
const loadedPlugins = new Map<string, LoadedPlugin>();

// Get allowed modules from environment
const ALLOWED_MODULES = Deno.env.get("ALLOWED_MODULES")?.split(",") || [];
const DEFAULT_MODULES = Deno.env.get("DEFAULT_MODULES")?.split(",") || [];
const MODULE_TIMEOUT = parseInt(Deno.env.get("MODULE_TIMEOUT") || "5000");

// Load default modules on startup
for (const modulePath of DEFAULT_MODULES) {
  if (modulePath) {
    try {
      const module = await import(modulePath) as PluginModule;
      loadedPlugins.set(modulePath, {
        module,
        path: modulePath,
        loadedAt: Date.now()
      });
      if (module.init) {
        module.init(app);
      }
    } catch (error) {
      console.error(`Failed to load default module ${modulePath}:`, error);
    }
  }
}

app.get("/", (c) => {
  return c.json({
    status: "running",
    plugins: Array.from(loadedPlugins.entries()).map(([path, plugin]) => ({
      path,
      name: plugin.module.name,
      version: plugin.module.version,
      loadedAt: new Date(plugin.loadedAt).toISOString()
    }))
  });
});

app.post("/load", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const modulePath = body.module || c.req.query("module");
  
  if (!modulePath) {
    return c.json({ error: "Module path required" }, 400);
  }

  // Check if module is in allowed list
  if (ALLOWED_MODULES.length > 0 && !ALLOWED_MODULES.includes(modulePath)) {
    return c.json({ error: "Module not in allowed list" }, 403);
  }

  // Check if already loaded
  if (loadedPlugins.has(modulePath)) {
    return c.json({ 
      message: "Module already loaded",
      module: {
        name: loadedPlugins.get(modulePath)!.module.name,
        version: loadedPlugins.get(modulePath)!.module.version
      }
    });
  }

  try {
    // Set timeout for module loading
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), MODULE_TIMEOUT);

    const modulePromise = import(modulePath);
    const module = await Promise.race([
      modulePromise,
      new Promise((_, reject) => {
        controller.signal.addEventListener('abort', () => {
          reject(new Error('Module load timeout'));
        });
      })
    ]) as PluginModule;

    clearTimeout(timeoutId);

    // Validate module structure
    if (!module.name || !module.version) {
      throw new Error("Invalid module: missing name or version");
    }

    loadedPlugins.set(modulePath, {
      module,
      path: modulePath,
      loadedAt: Date.now()
    });

    // Initialize module if it has init function
    if (module.init) {
      module.init(app);
    }

    return c.json({
      success: true,
      module: {
        name: module.name,
        version: module.version,
        path: modulePath
      }
    });
  } catch (error) {
    return c.json({ 
      error: "Failed to load module",
      details: error instanceof Error ? error.message : String(error)
    }, 500);
  }
});

app.post("/unload", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const modulePath = body.module || c.req.query("module");
  
  if (!modulePath) {
    return c.json({ error: "Module path required" }, 400);
  }

  const plugin = loadedPlugins.get(modulePath);
  if (!plugin) {
    return c.json({ error: "Module not loaded" }, 404);
  }

  // Call cleanup if available
  if (plugin.module.cleanup) {
    try {
      plugin.module.cleanup();
    } catch (error) {
      console.error(`Cleanup failed for ${modulePath}:`, error);
    }
  }

  loadedPlugins.delete(modulePath);
  
  return c.json({
    success: true,
    message: "Module unloaded",
    module: {
      name: plugin.module.name,
      version: plugin.module.version
    }
  });
});

app.post("/process", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const modulePath = body.module || c.req.query("module");
  const data = body.data || {};
  
  if (!modulePath) {
    return c.json({ error: "Module path required" }, 400);
  }

  const plugin = loadedPlugins.get(modulePath);
  if (!plugin) {
    // Try to load module dynamically
    if (ALLOWED_MODULES.length > 0 && !ALLOWED_MODULES.includes(modulePath)) {
      return c.json({ error: "Module not allowed" }, 403);
    }

    try {
      const module = await import(modulePath) as PluginModule;
      if (!module.process) {
        return c.json({ error: "Module has no process function" }, 400);
      }

      const result = await module.process(data);
      return c.json({
        success: true,
        result,
        module: {
          name: module.name,
          version: module.version
        }
      });
    } catch (error) {
      return c.json({ 
        error: "Failed to load and process",
        details: error instanceof Error ? error.message : String(error)
      }, 500);
    }
  }

  if (!plugin.module.process) {
    return c.json({ error: "Module has no process function" }, 400);
  }

  try {
    const result = await plugin.module.process(data);
    return c.json({
      success: true,
      result,
      module: {
        name: plugin.module.name,
        version: plugin.module.version
      }
    });
  } catch (error) {
    return c.json({ 
      error: "Processing failed",
      details: error instanceof Error ? error.message : String(error)
    }, 500);
  }
});

app.get("/plugins", (c) => {
  const plugins = Array.from(loadedPlugins.entries()).map(([path, plugin]) => ({
    path,
    name: plugin.module.name,
    version: plugin.module.version,
    hasInit: !!plugin.module.init,
    hasProcess: !!plugin.module.process,
    hasCleanup: !!plugin.module.cleanup,
    loadedAt: new Date(plugin.loadedAt).toISOString()
  }));

  return c.json({
    loaded: plugins,
    allowed: ALLOWED_MODULES,
    defaults: DEFAULT_MODULES
  });
});

// Health check endpoint
app.get("/health", (c) => {
  return c.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    plugins: loadedPlugins.size
  });
});

// Cleanup on shutdown (Deno Deploy handles this)
globalThis.addEventListener("unload", () => {
  for (const [_, plugin] of loadedPlugins) {
    if (plugin.module.cleanup) {
      try {
        plugin.module.cleanup();
      } catch (error) {
        console.error("Cleanup error:", error);
      }
    }
  }
});

Deno.serve(app.fetch);