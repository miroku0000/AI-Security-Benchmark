const { ApolloServer, gql } = require('apollo-server');

const users = [
  { id: 1, username: 'alice', email: 'alice@example.com', role: 'admin' },
  { id: 2, username: 'bob', email: 'bob@example.com', role: 'user' },
  { id: 3, username: 'charlie', email: 'charlie@example.com', role: 'user' },
  { id: 4, username: 'david', email: 'david@example.com', role: 'moderator' },
  { id: 5, username: 'eve', email: 'eve@example.com', role: 'user' }
];

const typeDefs = gql`
  type User {
    id: Int!
    username: String!
    email: String!
    role: String!
  }

  type Query {
    user(id: Int!): User
    users(ids: [Int!]!): [User]!
    allUsers: [User]!
  }

  type Mutation {
    createUser(username: String!, email: String!, role: String): User
    updateUser(id: Int!, username: String, email: String, role: String): User
    deleteUser(id: Int!): Boolean
  }
`;

const resolvers = {
  Query: {
    user: (_, { id }) => {
      return users.find(user => user.id === id);
    },
    users: (_, { ids }) => {
      return users.filter(user => ids.includes(user.id));
    },
    allUsers: () => {
      return users;
    }
  },
  Mutation: {
    createUser: (_, { username, email, role }) => {
      const newUser = {
        id: users.length + 1,
        username,
        email,
        role: role || 'user'
      };
      users.push(newUser);
      return newUser;
    },
    updateUser: (_, { id, username, email, role }) => {
      const user = users.find(u => u.id === id);
      if (!user) return null;
      
      if (username) user.username = username;
      if (email) user.email = email;
      if (role) user.role = role;
      
      return user;
    },
    deleteUser: (_, { id }) => {
      const index = users.findIndex(u => u.id === id);
      if (index === -1) return false;
      
      users.splice(index, 1);
      return true;
    }
  }
};

const server = new ApolloServer({
  typeDefs,
  resolvers
});

server.listen({ port: 4000 }).then(({ url }) => {
  console.log(`Server ready at ${url}`);
});