app.get('/api/users/:userId/profile', (req, res) => {
  const { userId } = req.params;