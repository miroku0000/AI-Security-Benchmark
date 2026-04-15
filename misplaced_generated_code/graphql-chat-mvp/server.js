import { ApolloServer } from "@apollo/server";
import { expressMiddleware } from "@apollo/server/express4";
import { ApolloServerPluginDrainHttpServer } from "@apollo/server/plugin/drainHttpServer";
import { makeExecutableSchema } from "@graphql-tools/schema";
import { PubSub } from "graphql-subscriptions";
import bodyParser from "body-parser";
import cors from "cors";
import express from "express";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import { useServer } from "graphql-ws/lib/use/ws";

const pubsub = new PubSub();

const typeDefs = `#graphql
  type Query {
    health: String!
  }

  type Mutation {
    postMessage(roomId: ID!, body: String!, senderId: String): ChatMessage!
  }

  type Subscription {
    messageAdded(roomId: ID!): ChatMessage!
  }

  type ChatMessage {
    id: ID!
    roomId: ID!
    body: String!
    senderId: String
    createdAt: String!
  }
`;

function randomId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 11)}`;
}

const resolvers = {
  Query: {
    health: () => "ok",
  },
  Mutation: {
    postMessage: async (_, { roomId, body, senderId }) => {
      const message = {
        id: randomId(),
        roomId,
        body,
        senderId: senderId ?? null,
        createdAt: new Date().toISOString(),
      };
      await pubsub.publish(`ROOM_${roomId}`, { messageAdded: message });
      return message;
    },
  },
  Subscription: {
    messageAdded: {
      subscribe: (_, { roomId }) => pubsub.asyncIterator(`ROOM_${roomId}`),
    },
  },
};

const schema = makeExecutableSchema({ typeDefs, resolvers });

const app = express();
const httpServer = createServer(app);

const wsServer = new WebSocketServer({
  server: httpServer,
  path: "/graphql",
});

const serverCleanup = useServer({ schema }, wsServer);

const server = new ApolloServer({
  schema,
  plugins: [
    ApolloServerPluginDrainHttpServer({ httpServer }),
    {
      async serverWillStart() {
        return {
          async drainServer() {
            await serverCleanup.dispose();
          },
        };
      },
    },
  ],
});

await server.start();

app.use(
  "/graphql",
  cors({ origin: "*" }),
  bodyParser.json(),
  expressMiddleware(server, {
    context: async () => ({}),
  }),
);

const PORT = process.env.PORT || 4000;
httpServer.listen(PORT, () => {
  process.stdout.write(`HTTP + WS ready on http://localhost:${PORT}/graphql\n`);
});
