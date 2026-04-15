const { url } = await startStandaloneServer(server, {
    listen: { port: process.env.PORT ? Number(process.env.PORT) : 4000 },
    context: async ({ req }) => {
      const userId = req.headers['x-user-id'] || 'user_123';