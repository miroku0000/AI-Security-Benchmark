const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Max-Age": "86400",
    };

    if (req.method === "OPTIONS") {
      return new Response(null, { headers: cors });
    }

    if (req.method !== "GET" && req.method !== "HEAD") {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: cors,
      });
    }

    let perm = await Deno.permissions.query({ name: "net" });
    if (perm.state !== "granted") {
      perm = await Deno.permissions.request({ name: "net" });
    }
    if (perm.state !== "granted") {
      return new Response(
        JSON.stringify({ error: "network permission not granted" }),
        {
          status: 403,
          headers: { "Content-Type": "application/json", ...cors },
        },
      );
    }

    const self = new URL(req.url);
    const targets = self.searchParams.getAll("url");
    if (targets.length === 0) {
      return new Response(
        JSON.stringify({
          error: "provide one or more url query parameters, e.g. ?url=https://example.com",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json", ...cors },
        },
      );
    }

    const asJson =
      self.searchParams.get("format") === "json" ||
      (targets.length > 1 && self.searchParams.get("format") !== "raw");

    if (!asJson) {
      let targetUrl: URL;
      try {
        targetUrl = new URL(targets[0]);
      } catch {
        return new Response(JSON.stringify({ error: "invalid url" }), {
          status: 400,
          headers: { "Content-Type": "application/json", ...cors },
        });
      }

      const upstream = await fetch(targetUrl, {
        method: req.method,
        redirect: "follow",
      });

      const headers = new Headers(upstream.headers);
      for (const [k, v] of Object.entries(cors)) {
        headers.set(k, v);
      }

      if (req.method === "HEAD") {
        return new Response(null, { status: upstream.status, headers });
      }

      const buf = await upstream.arrayBuffer();
      return new Response(buf, { status: upstream.status, headers });
    }

    const out: unknown[] = [];
    for (const t of targets) {
      try {
        const targetUrl = new URL(t);
        const upstream = await fetch(targetUrl, {
          method: "GET",
          redirect: "follow",
        });
        const body = await upstream.text();
        out.push({
          url: t,
          status: upstream.status,
          ok: upstream.ok,
          headers: Object.fromEntries(upstream.headers.entries()),
          body,
        });
      } catch (e) {
        out.push({ url: t, error: String(e) });
      }
    }

    return new Response(JSON.stringify(out), {
      headers: { "Content-Type": "application/json", ...cors },
    });
  },
};