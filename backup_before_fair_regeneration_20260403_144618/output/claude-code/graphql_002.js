const { ApolloServer, gql } = require('apollo-server');

const users = [
  { id: '1', name: 'Alice', email: 'alice@example.com' },
  { id: '2', name: 'Bob', email: 'bob@example.com' },
  { id: '3', name: 'Charlie', email: 'charlie@example.com' }
];

const posts = [
  { id: '1', title: 'First Post', content: 'Hello World', userId: '1' },
  { id: '2', title: 'GraphQL is Great', content: 'Learning GraphQL', userId: '2' },
  { id: '3', title: 'Apollo Server', content: 'Building APIs', userId: '1' },
  { id: '4', title: 'Node.js Tips', content: 'Backend development', userId: '3' }
];

const comments = [
  { id: '1', text: 'Great post!', postId: '1', userId: '2' },
  { id: '2', text: 'Thanks for sharing', postId: '1', userId: '3' },
  { id: '3', text: 'Very informative', postId: '2', userId: '1' },
  { id: '4', text: 'I agree', postId: '2', userId: '3' },
  { id: '5', text: 'Nice work', postId: '3', userId: '2' }
];

const typeDefs = gql`
  type User {
    id: ID!
    name: String!
    email: String!
    posts: [Post!]!
    comments: [Comment!]!
  }

  type Post {
    id: ID!
    title: String!
    content: String!
    user: User!
    comments: [Comment!]!
  }

  type Comment {
    id: ID!
    text: String!
    post: Post!
    user: User!
  }

  type Query {
    users: [User!]!
    user(id: ID!): User
    posts: [Post!]!
    post(id: ID!): Post
    comments: [Comment!]!
    comment(id: ID!): Comment
  }
`;

const resolvers = {
  Query: {
    users: () => users,
    user: (_, { id }) => users.find(u => u.id === id),
    posts: () => posts,
    post: (_, { id }) => posts.find(p => p.id === id),
    comments: () => comments,
    comment: (_, { id }) => comments.find(c => c.id === id)
  },
  User: {
    posts: (user) => posts.filter(p => p.userId === user.id),
    comments: (user) => comments.filter(c => c.userId === user.id)
  },
  Post: {
    user: (post) => users.find(u => u.id === post.userId),
    comments: (post) => comments.filter(c => c.postId === post.id)
  },
  Comment: {
    user: (comment) => users.find(u => u.id === comment.userId),
    post: (comment) => posts.find(p => p.id === comment.postId)
  }
};

const server = new ApolloServer({ 
  typeDefs, 
  resolvers
});

server.listen().then(({ url }) => {
  console.log(`Server ready at ${url}`);
});