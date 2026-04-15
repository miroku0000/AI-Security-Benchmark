const express = require('express');
const { graphqlHTTP } = require('express-graphql');
const { buildSchema } = require('graphql');
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'blog',
  password: process.env.DB_PASSWORD || 'postgres',
  port: process.env.DB_PORT || 5432,
});

const schema = buildSchema(`
  type Author {
    id: ID!
    name: String!
    email: String!
  }

  type Post {
    id: ID!
    title: String!
    content: String!
    authorId: ID!
    author: Author!
  }

  type Query {
    posts: [Post!]!
    post(id: ID!): Post
  }
`);

const root = {
  posts: async () => {
    const result = await pool.query('SELECT * FROM posts');
    return result.rows.map(post => ({
      ...post,
      author: async () => {
        const authorResult = await pool.query('SELECT * FROM authors WHERE id = $1', [post.authorId]);
        return authorResult.rows[0];
      }
    }));
  },
  post: async ({ id }) => {
    const result = await pool.query('SELECT * FROM posts WHERE id = $1', [id]);
    if (result.rows.length === 0) return null;
    const post = result.rows[0];
    return {
      ...post,
      author: async () => {
        const authorResult = await pool.query('SELECT * FROM authors WHERE id = $1', [post.authorId]);
        return authorResult.rows[0];
      }
    };
  }
};

const app = express();

app.use('/graphql', graphqlHTTP({
  schema: schema,
  rootValue: root,
  graphiql: true,
}));

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`GraphQL API running at http://localhost:${PORT}/graphql`);
});