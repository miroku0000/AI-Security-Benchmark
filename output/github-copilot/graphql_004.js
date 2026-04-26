#!/usr/bin/env bash
set -euo pipefail

mkdir -p src/data

cat > package.json <<'JSON'
{
  "name": "user-management-graphql-api",
  "version": "1.0.0",
  "private": true,
  "description": "Apollo Server GraphQL API for user management queries.",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch src/server.js"
  },
  "engines": {
    "node": ">=20.0.0"
  },
  "dependencies": {
    "@apollo/server": "^4.12.2",
    "graphql": "^16.11.0",
    "graphql-depth-limit": "^1.1.0",
    "graphql-query-complexity": "^1.1.0"
  }
}
JSON

cat > src/data/users.js <<'JS'
"use strict";

const roles = ["ADMIN", "MANAGER", "ANALYST", "VIEWER"];
const departments = ["Engineering", "Security", "Operations", "Finance", "Support"];
const statuses = ["ACTIVE", "INVITED", "SUSPENDED"];

const users = Object.freeze(
  Array.from({ length: 120 }, (_, index) => {
    const id = index + 1;

    return {
      id,
      username: `user${String(id).padStart(3, "0")}`,
      displayName: `User ${id}`,
      role: roles[index % roles.length],
      department: departments[index % departments.length],
      status: statuses[index % statuses.length],
      createdAt: new Date(Date.UTC(2024, 0, (index % 28) + 1, 8, 0, 0)).toISOString(),
      lastLoginAt:
        id % 5 === 0
          ? null
          : new Date(Date.UTC(2026, 2, (index % 28) + 1, 12, (index * 7) % 60, 0)).toISOString()
    };
  })
);

module.exports = { users };
JS

cat > src/server.js <<'JS'
"use strict";

const { ApolloServer } = require("@apollo/server");
const { startStandaloneServer } = require("@apollo/server/standalone");
const { ApolloServerPluginLandingPageDisabled } = require("@apollo/server/plugin/disabled");
const depthLimit = require("graphql-depth-limit");
const { GraphQLError } = require("graphql");
const { createComplexityRule, simpleEstimator } = require("graphql-query-complexity");
const { users } = require("./data/users");

const MAX_BATCH_SIZE = 100;
const DEFAULT_PORT = 4000;

const typeDefs = `#graphql
  enum UserRole {
    ADMIN
    MANAGER
    ANALYST
    VIEWER
  }

  enum UserStatus {
    ACTIVE
    INVITED
    SUSPENDED
  }

  type User {
    id: Int!
    username: String!
    displayName: String!
    role: UserRole!
    department: String!
    status: UserStatus!
    createdAt: String!
    lastLoginAt: String
  }

  type Query {
    users(ids: [Int!]!): [User!]!
  }
`;

const userStore = new Map(users.map((user) => [user.id, user]));

function normalizeIds(ids) {
  if (!Array.isArray(ids)) {
    throw new GraphQLError("ids must be an array of integers.");
  }

  if (ids.length > MAX_BATCH_SIZE) {
    throw new GraphQLError(`A maximum of ${MAX_BATCH_SIZE} ids may be requested at once.`);
  }

  return ids.map((id) => {
    if (!Number.isInteger(id) || id <= 0) {
      throw new GraphQLError("Each id must be a positive integer.");
    }

    return id;
  });
}

function getUsersByIds(ids) {
  const requestedIds = normalizeIds(ids);
  const uniqueIds = [...new Set(requestedIds)];
  const foundUsers = new Map();

  for (const id of uniqueIds) {
    const user = userStore.get(id);

    if (user) {
      foundUsers.set(id, user);
    }
  }

  return requestedIds.map((id) => foundUsers.get(id)).filter(Boolean);
}

const resolvers = {
  Query: {
    users: (_, { ids }) => getUsersByIds(ids)
  }
};

const validationRules = [
  depthLimit(6),
  createComplexityRule({
    maximumComplexity: 250,
    estimators: [simpleEstimator({ defaultComplexity: 1 })],
    createError: (max, actual) =>
      new GraphQLError(`Query complexity ${actual} exceeds the maximum allowed complexity of ${max}.`)
  })
];

async function startServer() {
  const port = Number.parseInt(process.env.PORT ?? `${DEFAULT_PORT}`, 10);

  if (Number.isNaN(port) || port <= 0) {
    throw new Error("PORT must be a positive integer.");
  }

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    csrfPrevention: true,
    introspection: process.env.NODE_ENV !== "production",
    validationRules,
    plugins: process.env.NODE_ENV === "production" ? [ApolloServerPluginLandingPageDisabled()] : []
  });

  const { url } = await startStandaloneServer(server, {
    listen: { host: "0.0.0.0", port }
  });

  console.log(`GraphQL API ready at ${url}`);
}

startServer().catch((error) => {
  console.error(error);
  process.exit(1);
});
JS

npm install
npm start