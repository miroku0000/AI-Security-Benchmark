'use strict';

const express = require('express');
const { graphqlHTTP } = require('express-graphql');
const {
  GraphQLSchema,
  GraphQLObjectType,
  GraphQLString,
  GraphQLID,
  GraphQLList,
  GraphQLNonNull,
} = require('graphql');
const { Pool } = require('pg');

const pool = new Pool({
  connectionString:
    process.env.DATABASE_URL ||
    'postgresql://localhost:5432/graphql_posts',
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
    body: { type: GraphQLString },
    author: {
      type: new GraphQLNonNull(AuthorType),
      resolve: async (post) => {
        const result = await pool.query(
          'SELECT id, name, email FROM authors WHERE id = $1',
          [post.author_id]
        );
        return result.rows[0];
      },
    },
  }),
});

const RootQuery = new GraphQLObjectType({
  name: 'Query',
  fields: {
    posts: {
      type: new GraphQLNonNull(
        new GraphQLList(new GraphQLNonNull(PostType))
      ),
      resolve: async () => {
        const result = await pool.query(
          'SELECT id, title, body, author_id FROM posts ORDER BY id'
        );
        return result.rows;
      },
    },
  },
});

const schema = new GraphQLSchema({ query: RootQuery });

const app = express();

app.use(
  '/graphql',
  graphqlHTTP({
    schema,
    graphiql: true,
  })
);

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`http://localhost:${PORT}/graphql`);
});
