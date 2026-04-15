function collectSpecifiers(req: Request): string[] {
  const url = new URL(req.url);
  const fromEnv =
    Deno.env.get("MODULE_PATHS") ||
    Deno.env.get("PLUGIN_PATHS") ||
    Deno.env.get("MODULE_PATH") ||
    Deno.env.get("PLUGIN_MODULE") ||
    "";
  const envList = fromEnv.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
  const qp = url.searchParams.getAll("module");
  const qpCsv = url.searchParams.get("modules")?.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean) ?? [];
  return [...new Set([...envList, ...qp, ...qpCsv])];
}

type Loaded = {
  specifier: string;
  ok: boolean;
  exports?: string[];
  error?: string;
};

Deno.serve(async (req) => {
  const specifiers = collectSpecifiers(req);

  if (specifiers.length === 0) {
    return new Response(
      "Set MODULE_PATHS (or MODULE_PATH) or pass ?module= or ?modules= with module specifiers.",
      { status: 400, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }

  if (specifiers.length === 1) {
    const specifier = specifiers[0];
    try {
      const mod = await import(specifier);
      const def = mod.default;
      if (typeof def === "function") {
        return await def(req);
      }
      if (def && typeof def === "object" && "handle" in def && typeof (def as { handle: unknown }).handle === "function") {
        return await (def as { handle: (r: Request) => Response | Promise<Response> }).handle(req);
      }
      const loaded: Loaded = {
        specifier,
        ok: true,
        exports: Object.keys(mod),
      };
      return new Response(JSON.stringify(loaded, null, 2), {
        headers: { "content-type": "application/json; charset=utf-8" },
      });
    } catch (e) {
      const err = e instanceof Error ? e.message : String(e);
      return new Response(JSON.stringify({ specifier, ok: false, error: err }, null, 2), {
        status: 500,
        headers: { "content-type": "application/json; charset=utf-8" },
      });
    }
  }

  const loaded: Loaded[] = [];
  for (const specifier of specifiers) {
    try {
      const mod = await import(specifier);
      loaded.push({ specifier, ok: true, exports: Object.keys(mod) });
    } catch (e) {
      loaded.push({
        specifier,
        ok: false,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  return new Response(JSON.stringify({ modules: loaded }, null, 2), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
});
