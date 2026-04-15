const QueryType = new GraphQLObjectType({
  name: 'Query',
  fields: {
    posts: {
      type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(PostType))),
      resolve: async () => {
        const result = await pool.query(
          'SELECT id, title, body, author_id FROM posts ORDER BY id'
        );
        return result.rows;
      },
    },
    post: {
      type: PostType,
      args: {
        id: { type: new GraphQLNonNull(GraphQLInt) },
      },
      resolve: async (_, args) => {
        const result = await pool.query(
          'SELECT id, title, body, author_id FROM posts WHERE id = $1',
          [args.id]
        );
        return result.rows[0] || null;
      },
    },
    authors: {
      type: new GraphQLNonNull(new GraphQLList(new GraphQLNonNull(AuthorType))),
      resolve: async () => {
        const result = await pool.query(
          'SELECT id, name, email FROM authors ORDER BY id'
        );
        return result.rows;
      },
    },
    author: {
      type: AuthorType,
      args: {
        id: { type: new GraphQLNonNull(GraphQLInt) },
      },
      resolve: async (_, args) => {
        const result = await pool.query(
          'SELECT id, name, email FROM authors WHERE id = $1',
          [args.id]
        );
        return result.rows[0] || null;
      },
    },
  },
});