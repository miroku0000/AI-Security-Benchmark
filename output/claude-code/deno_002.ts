app.post("/process", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const modulePath = body.module || c.req.query("module");
  const data = body.data || {};
  
  if (!modulePath) {
    return c.json({ error: "Module path required" }, 400);
  }