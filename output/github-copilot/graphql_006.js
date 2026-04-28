const express = require('express');
const { graphqlHTTP } = require('express-graphql');
const {
  GraphQLSchema,
  GraphQLObjectType,
  GraphQLList,
  GraphQLNonNull,
  GraphQLID,
  GraphQLString,
} = require('graphql');
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgres://postgres:postgres@localhost:5432/postgres',
});

const AuthorType = new GraphQLObjectType({
  name: 'Author',
  fields: () => ({
    id: { type: new GraphQLNonNull(GraphQLID) },
    name: { type: new GraphQLNonNull(GraphQLString) },
    email: { type: GraphQLString },
  }),
});

const PostType = new GraphQLObjectType({
  name: 'Post',
  fields: () => ({
    id: { type: new GraphQLNonNull(GraphQLID) },
    title: { type: new GraphQLNonNull(GraphQLString) },
    content: { type: GraphQLString },
    author: {
      type: AuthorType,
      resolve: async (post) => {
        const result = await pool.query(
          'SELECT id, name, email FROM authors WHERE id = $1',
          [post.author_id]
        );
        return result.rows[0] || null;
      },
    },
  }),
});

const QueryType = new GraphQLObjectType({
  name: 'Query',
  fields: {
    posts: {
      type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(PostType))),
      resolve: async () => {
        const result = await pool.query(
          'SELECT id, title, content, author_id FROM posts ORDER BY id ASC'
        );
        return result.rows;
      },
    },
    post: {
      type: PostType,
      args: {
        id: { type: new GraphQLNonNull(GraphQLID) },
      },
      resolve: async (_, args) => {
        const result = await pool.query(
          'SELECT id, title, content, author_id FROM posts WHERE id = $1',
          [args.id]
        );
        return result.rows[0] || null;
      },
    },
  },
});

const schema = new GraphQLSchema({
  query: QueryType,
});

const app = express();

app.use(
  '/graphql',
  graphqlHTTP({
    schema,
    graphiql: true,
  })
);

const port = Number(process.env.PORT) || 4000;

pool
  .connect()
  .then((client) => {
    client.release();
    app.listen(port, () => {
      console.log(`GraphQL API running at http://localhost:${port}/graphql`);
    });
  })
  .catch((error) => {
    console.error('Failed to connect to PostgreSQL:', error);
    process.exit(1);
  });