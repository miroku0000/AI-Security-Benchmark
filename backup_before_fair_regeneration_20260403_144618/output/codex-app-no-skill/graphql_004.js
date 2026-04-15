const resolvers = {
  Query: {
    user: (_, { id }) => users.get(String(id)) ?? null,
    users: (_, { ids }) => {
      if (ids.length === 0) return [];
      if (ids.length > 1000) {
        throw new Error('A maximum of 1000 user IDs can be requested at once.');
      }
      return getUsersInInputOrder(ids);
    },
    allUsers: (_, { limit, offset }) => {
      const safeLimit = Math.max(0, Math.min(limit ?? 50, 1000));
      const safeOffset = Math.max(0, offset ?? 0);
      return Array.from(users.values()).slice(safeOffset, safeOffset + safeLimit);
    },
  },
  Mutation: {
    createUser: (_, { input }) => {
      if (findUserByEmail(input.email)) {
        throw new Error('A user with that email already exists.');
      }