const { ApolloServer, gql, PubSub } = require('apollo-server');

const pubsub = new PubSub();

const messages = [];
const rooms = {};

const typeDefs = gql`
  type Message {
    id: ID!
    roomId: String!
    userId: String!
    content: String!
    timestamp: String!
  }

  type Query {
    messages(roomId: String!): [Message!]!
    rooms: [String!]!
  }

  type Mutation {
    sendMessage(roomId: String!, userId: String!, content: String!): Message!
    createRoom(roomId: String!): String!
  }

  type Subscription {
    messageAdded(roomId: String!): Message!
  }
`;

const resolvers = {
  Query: {
    messages: (_, { roomId }) => {
      return messages.filter(msg => msg.roomId === roomId);
    },
    rooms: () => {
      return Object.keys(rooms);
    }
  },
  Mutation: {
    sendMessage: (_, { roomId, userId, content }) => {
      const message = {
        id: String(messages.length + 1),
        roomId,
        userId,
        content,
        timestamp: new Date().toISOString()
      };
      
      messages.push(message);
      pubsub.publish(`MESSAGE_ADDED_${roomId}`, { messageAdded: message });
      
      return message;
    },
    createRoom: (_, { roomId }) => {
      if (!rooms[roomId]) {
        rooms[roomId] = true;
      }
      return roomId;
    }
  },
  Subscription: {
    messageAdded: {
      subscribe: (_, { roomId }) => {
        if (!rooms[roomId]) {
          rooms[roomId] = true;
        }
        return pubsub.asyncIterator([`MESSAGE_ADDED_${roomId}`]);
      }
    }
  }
};

const server = new ApolloServer({
  typeDefs,
  resolvers,
  subscriptions: {
    path: '/graphql'
  }
});

server.listen().then(({ url, subscriptionsUrl }) => {
  console.log(`Server ready at ${url}`);
  console.log(`Subscriptions ready at ${subscriptionsUrl}`);
});