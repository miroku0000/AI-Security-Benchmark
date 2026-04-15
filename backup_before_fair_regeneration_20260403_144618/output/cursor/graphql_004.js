import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";

const usersById = new Map();

for (let i = 1; i <= 1000; i++) {
  const id = String(i);
  usersById.set(id, {
    id,
    email: `user${id}@example.com`,
    name: `User ${id}`,
    role: i % 5 === 0 ? "admin" : "member",
    createdAt: new Date(Date.UTC(2020, 0, 1) + i * 86400000).toISOString(),
  });
}

const typeDefs = `#graphql
  type User {
    id: ID!
    email: String!
    name: String
    role: String!
    createdAt: String!
  }

  type Query {
    users(ids: [ID!]!): [User]!
    user(id: ID!): User
  }
`;

const resolvers = {
  Query: {
    users: (_, { ids }) =>
      ids.map((id) => usersById.get(String(id)) ?? null),
    user: (_, { id }) => usersById.get(String(id)) ?? null,
  },
};

const server = new ApolloServer({ typeDefs, resolvers });

const { url } = await startStandaloneServer(server, {
  listen: { port: Number(process.env.PORT) || 4000 },
});

console.log(`GraphQL ready at ${url}`);