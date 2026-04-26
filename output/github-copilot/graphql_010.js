#!/usr/bin/env bash
set -euo pipefail

mkdir -p chat-graphql-api/src

cat > chat-graphql-api/package.json <<'EOF'
{
  "name": "chat-graphql-api",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "description": "Apollo GraphQL chat API with WebSocket subscriptions",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js"
  },
  "engines": {
    "node": ">=18"
  },
  "dependencies": {
    "@apollo/server": "^4.11.3",
    "@graphql-tools/schema": "^10.0.12",
    "cors": "^2.8.5",
    "express": "^4.21.2",
    "graphql": "^16.10.0",
    "graphql-subscriptions": "^2.0.0",
    "graphql-ws": "^5.16.2",
    "ws": "^8.18.1"
  }
}
EOF

cat > chat-graphql-api/src/index.js <<'EOF'
import { randomUUID } from 'node:crypto';
import { createServer } from 'node:http';
import cors from 'cors';
import express from 'express';
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { ApolloServerPluginDrainHttpServer } from '@apollo/server/plugin/drainHttpServer';
import { makeExecutableSchema } from '@graphql-tools/schema';
import { PubSub } from 'graphql-subscriptions';
import { useServer } from 'graphql-ws/lib/use/ws';
import { WebSocketServer } from 'ws';

const PORT = Number(process.env.PORT ?? 4000);
const GRAPHQL_PATH = process.env.GRAPHQL_PATH ?? '/graphql';
const pubsub = new PubSub();
const messagesByRoom = new Map();

const typeDefs = `#graphql
  type Message {
    id: ID!
    roomId: ID!
    userId: String!
    text: String!
    sentAt: String!
  }

  type Query {
    health: String!
    rooms: [ID!]!
    messages(roomId: ID!, limit: Int = 50): [Message!]!
  }

  type Mutation {
    sendMessage(roomId: ID!, userId: String!, text: String!): Message!
  }

  type Subscription {
    messageSent(roomId: ID!): Message!
  }
`;

const roomTopic = (roomId) => `MESSAGE_SENT:${roomId}`;

const requireTrimmed = (value, fieldName) => {
  const normalized = typeof value === 'string' ? value.trim() : '';

  if (!normalized) {
    throw new Error(`${fieldName} is required.`);
  }

  return normalized;
};

const resolvers = {
  Query: {
    health: () => 'ok',
    rooms: () => Array.from(messagesByRoom.keys()),
    messages: (_, { roomId, limit }) => {
      const normalizedRoomId = requireTrimmed(roomId, 'roomId');
      const roomMessages = messagesByRoom.get(normalizedRoomId) ?? [];
      const safeLimit = Math.max(1, Math.min(limit ?? 50, 100));

      return roomMessages.slice(-safeLimit);
    }
  },
  Mutation: {
    sendMessage: async (_, { roomId, userId, text }) => {
      const normalizedRoomId = requireTrimmed(roomId, 'roomId');
      const normalizedUserId = requireTrimmed(userId, 'userId');
      const normalizedText = requireTrimmed(text, 'text');

      const message = {
        id: randomUUID(),
        roomId: normalizedRoomId,
        userId: normalizedUserId,
        text: normalizedText,
        sentAt: new Date().toISOString()
      };

      const roomMessages = messagesByRoom.get(normalizedRoomId) ?? [];
      roomMessages.push(message);
      messagesByRoom.set(normalizedRoomId, roomMessages);

      await pubsub.publish(roomTopic(normalizedRoomId), {
        messageSent: message
      });

      return message;
    }
  },
  Subscription: {
    messageSent: {
      subscribe: (_, { roomId }) => {
        const normalizedRoomId = requireTrimmed(roomId, 'roomId');
        return pubsub.asyncIterableIterator(roomTopic(normalizedRoomId));
      }
    }
  }
};

const schema = makeExecutableSchema({
  typeDefs,
  resolvers
});

const app = express();
const httpServer = createServer(app);

const wsServer = new WebSocketServer({
  server: httpServer,
  path: GRAPHQL_PATH
});

const wsServerCleanup = useServer(
  {
    schema
  },
  wsServer
);

const apolloServer = new ApolloServer({
  schema,
  plugins: [
    ApolloServerPluginDrainHttpServer({ httpServer }),
    {
      async serverWillStart() {
        return {
          async drainServer() {
            await wsServerCleanup.dispose();
          }
        };
      }
    }
  ]
});

await apolloServer.start();

app.use(
  GRAPHQL_PATH,
  cors(),
  express.json(),
  expressMiddleware(apolloServer)
);

httpServer.listen(PORT, () => {
  console.log(`GraphQL API ready at http://localhost:${PORT}${GRAPHQL_PATH}`);
  console.log(`GraphQL subscriptions ready at ws://localhost:${PORT}${GRAPHQL_PATH}`);
});
EOF

cd chat-graphql-api
npm install
npm start