import crypto from "node:crypto";
import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";

const typeDefs = `#graphql
  scalar DateTime

  type User {
    id: ID!
    email: String!
    name: String!
    role: String!
    isActive: Boolean!
    createdAt: DateTime!
    updatedAt: DateTime!
  }

  type Query {
    user(id: ID!): User
    users(ids: [ID!]!): [User!]!
  }
`;

function isoNow() {
  return new Date().toISOString();
}

function makeUser({ id, email, name, role = "USER", isActive = true, createdAt, updatedAt }) {
  const now = isoNow();
  return {
    id: String(id),
    email,
    name,
    role,
    isActive,
    createdAt: createdAt ?? now,
    updatedAt: updatedAt ?? now,
  };
}

// Demo in-memory store; replace with DB in production.
const usersById = new Map(
  [
    makeUser({ id: 1, email: "admin@example.com", name: "Admin", role: "ADMIN" }),
    makeUser({ id: 2, email: "jane.doe@example.com", name: "Jane Doe" }),
    makeUser({ id: 3, email: "john.smith@example.com", name: "John Smith" }),
  ].map((u) => [u.id, u]),
);

const resolvers = {
  DateTime: {
    __serialize(value) {
      if (typeof value === "string") return value;
      if (value instanceof Date) return value.toISOString();
      return String(value);
    },
    __parseValue(value) {
      return new Date(value).toISOString();
    },
    __parseLiteral(ast) {
      // Basic support; avoid importing graphql AST types here.
      return ast?.value ? new Date(ast.value).toISOString() : null;
    },
  },
  Query: {
    user: async (_parent, { id }) => {
      const key = String(id);
      return usersById.get(key) ?? null;
    },
    users: async (_parent, { ids }) => {
      if (!Array.isArray(ids)) return [];
      if (ids.length > 5000) {
        throw new Error("Too many ids; max 5000.");
      }
      const seen = new Set();
      const out = [];
      for (const raw of ids) {
        const key = String(raw);
        if (seen.has(key)) continue;
        seen.add(key);
        const u = usersById.get(key);
        if (u) out.push(u);
      }
      return out;
    },
  },
};

function makeRequestId() {
  return crypto.randomBytes(12).toString("hex");
}

const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: true,
});

const port = Number(process.env.PORT || 4000);
const host = process.env.HOST || "0.0.0.0";

const { url } = await startStandaloneServer(server, {
  listen: { port, host },
  context: async ({ req }) => {
    const requestId = req?.headers?.["x-request-id"]?.toString() || makeRequestId();
    return { requestId };
  },
});

// eslint-disable-next-line no-console
console.log(`User GraphQL API ready at ${url}`);

