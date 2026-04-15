const values = columns.map((column) => payload.data[column]);
    const placeholders = columns.map((_, idx) => `$${idx + 1}`);
    const sql = `INSERT INTO "${table}" (${columns.map((c) => `"${c}"`).join(', ')}) VALUES (${placeholders.join(', ')}) RETURNING *`;
    const result = await pool.query(sql, values);
    return { rowCount: result.rowCount, rows: result.rows };
  }