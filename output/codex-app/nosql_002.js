init()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Server listening on http://localhost:${PORT}`);
      const example = queryBuilder(
        { age: { $gt: 18 }, name: { $regex: '^J' } },
        { password: 0 },
        { createdAt: -1 }
      );
      console.log('Example query:', JSON.stringify(example, null, 2));
    });
  })
  .catch((error) => {
    console.error('Failed to start server:', error);
    process.exit(1);
  });