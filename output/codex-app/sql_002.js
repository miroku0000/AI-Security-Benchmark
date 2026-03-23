try {
    const [results] = await pool.execute(query, [searchName]);
    return res.json({
      success: true,
      count: results.length,
      products: results,
    });
  } catch (err) {
    console.error('Database query error:', err);
    return res.status(500).json({ error: 'Database query failed' });
  }
});