app.get("/admin/users/search", async (req: Request<unknown, unknown, unknown, UserSearchFilters>, res: Response) => {
  try {
    const { sql, values } = buildUserSearchQuery(req.query);
    const result = await pool.query(sql, values);
    res.json({
      count: result.rowCount,
      rows: result.rows,
    });
  } catch (error) {
    console.error("Search failed:", error);
    res.status(500).json({ error: "Internal server error" });
  }
});