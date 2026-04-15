import http from 'node:http';
import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { makeExecutableSchema } from '@graphql-tools/schema';
import { WebSocketServer } from 'ws';
import { useServer } from 'graphql-ws/use/ws';
import { PubSub } from 'graphql-subscriptions';
import { GraphQLError } from 'graphql';
import { randomUUID } from 'node:crypto';

const PORT = Number(process.env.PORT || 4000);
const GRAPHQL_PATH = process.env.GRAPHQL_PATH || '/graphql';
const WS_PATH = process.env.WS_PATH || GRAPHQL_PATH;

const pubsub = new PubSub();

function roomTopic(roomId) {
  return `CHAT_ROOM:${roomId}`;
}

const typeDefs = /* GraphQL */ `
  scalar DateTime

  type Message {
    id: ID!
    roomId: ID!
    userId: ID!
    text: String!
    createdAt: DateTime!
  }

  type Query {
    health: String!
  }

  type Mutation {
    postMessage(roomId: ID!, userId: ID!, text: String!): Message!
  }

  type Subscription {
    messageAdded(roomId: ID!): Message!
  }
`;

const resolvers = {
  DateTime: {
    serialize(value) {
      if (value instanceof Date) return value.toISOString();
      if (typeof value === 'string') return value;
      if (typeof value === 'number') return new Date(value).toISOString();
      return null;
    },
    parseValue(value) {
      if (typeof value === 'string' || typeof value === 'number') return new Date(value);
      return null;
    },
    parseLiteral(ast) {
      if (ast.kind === 'StringValue') return new Date(ast.value);
      return null;
    },
  },
  Query: {
    health: () => 'ok',
  },
  Mutation: {
    postMessage: async (_parent, args) => {
      const roomId = String(args.roomId ?? '').trim();
      const userId = String(args.userId ?? '').trim();
      const text = String(args.text ?? '');

      if (!roomId) throw new GraphQLError('roomId is required');
      if (!userId) throw new GraphQLError('userId is required');
      if (!text.trim()) throw new GraphQLError('text must not be empty');

      const message = {
        id: randomUUID(),
        roomId,
        userId,
        text,
        createdAt: new Date(),
      };

      await pubsub.publish(roomTopic(roomId), { messageAdded: message });
      return message;
    },
  },
  Subscription: {
    messageAdded: {
      subscribe: (_parent, args) => {
        const roomId = String(args.roomId ?? '').trim();
        if (!roomId) throw new GraphQLError('roomId is required');
        return pubsub.asyncIterator(roomTopic(roomId));
      },
      resolve: (payload) => payload.messageAdded,
    },
  },
};

const schema = makeExecutableSchema({ typeDefs, resolvers });

const app = express();
app.use(cors());
app.get('/healthz', (_req, res) => res.status(200).send('ok'));

const httpServer = http.createServer(app);

const wsServer = new WebSocketServer({
  server: httpServer,
  path: WS_PATH,
});

const serverCleanup = useServer(
  {
    schema,
    context: async (ctx) => {
      const headers = ctx.extra?.request?.headers || {};
      return { headers };
    },
    onConnect: async () => {
      return true;
    },
  },
  wsServer
);

const apollo = new ApolloServer({
  schema,
  plugins: [
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

await apollo.start();

app.use(
  GRAPHQL_PATH,
  bodyParser.json({ limit: '1mb' }),
  expressMiddleware(apollo, {
    context: async ({ req }) => ({ headers: req.headers }),
  })
);

httpServer.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(
    JSON.stringify(
      {
        ok: true,
        port: PORT,
        graphqlPath: GRAPHQL_PATH,
        wsPath: WS_PATH,
      },
      null,
      2
    )
  );
});

