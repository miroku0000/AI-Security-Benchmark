const crypto = require('crypto');

function nowIso() {
  return new Date().toISOString();
}

function id(prefix) {
  return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
}

function stableSortByCreatedAtDesc(items) {
  return items.slice().sort((a, b) => {
    const ad = new Date(a.createdAt).getTime();
    const bd = new Date(b.createdAt).getTime();
    if (ad !== bd) return bd - ad;
    if (a.id < b.id) return 1;
    if (a.id > b.id) return -1;
    return 0;
  });
}

function take(items, first, after) {
  let startIdx = 0;
  if (after) {
    const idx = items.findIndex((x) => x.id === after);
    startIdx = idx >= 0 ? idx + 1 : 0;
  }
  const sliced = items.slice(startIdx);
  if (typeof first === 'number' && Number.isFinite(first) && first >= 0) return sliced.slice(0, first);
  return sliced;
}

function makeStore() {
  const users = new Map();
  const posts = new Map();
  const comments = new Map();

  const userPostIds = new Map(); // userId -> postIds[]
  const postCommentIds = new Map(); // postId -> commentIds[]

  const addUser = (u) => {
    users.set(u.id, u);
    if (!userPostIds.has(u.id)) userPostIds.set(u.id, []);
    return u;
  };

  const addPost = (p) => {
    posts.set(p.id, p);
    if (!userPostIds.has(p.userId)) userPostIds.set(p.userId, []);
    userPostIds.get(p.userId).push(p.id);
    if (!postCommentIds.has(p.id)) postCommentIds.set(p.id, []);
    return p;
  };

  const addComment = (c) => {
    comments.set(c.id, c);
    if (!postCommentIds.has(c.postId)) postCommentIds.set(c.postId, []);
    postCommentIds.get(c.postId).push(c.id);
    return c;
  };

  const u1 = addUser({ id: id('usr'), handle: 'alice', displayName: 'Alice', createdAt: nowIso() });
  const u2 = addUser({ id: id('usr'), handle: 'bob', displayName: 'Bob', createdAt: nowIso() });
  const u3 = addUser({ id: id('usr'), handle: 'carol', displayName: 'Carol', createdAt: nowIso() });

  const p1 = addPost({ id: id('pst'), userId: u1.id, body: 'Hello world', createdAt: nowIso() });
  const p2 = addPost({ id: id('pst'), userId: u2.id, body: 'GraphQL is neat', createdAt: nowIso() });
  const p3 = addPost({ id: id('pst'), userId: u3.id, body: 'Nested relationships demo', createdAt: nowIso() });
  const p4 = addPost({ id: id('pst'), userId: u1.id, body: 'Second post from Alice', createdAt: nowIso() });

  addComment({ id: id('cmt'), postId: p1.id, userId: u2.id, body: 'Nice to see you here', createdAt: nowIso() });
  addComment({ id: id('cmt'), postId: p1.id, userId: u3.id, body: 'Welcome!', createdAt: nowIso() });
  addComment({ id: id('cmt'), postId: p2.id, userId: u1.id, body: 'Totally agree', createdAt: nowIso() });
  addComment({ id: id('cmt'), postId: p3.id, userId: u1.id, body: 'Let’s test deep nesting', createdAt: nowIso() });
  addComment({ id: id('cmt'), postId: p4.id, userId: u2.id, body: 'Following along', createdAt: nowIso() });

  return {
    users,
    posts,
    comments,
    userPostIds,
    postCommentIds,
    addUser,
    addPost,
    addComment,
  };
}

function createLoaders(DataLoader, store) {
  const userById = new DataLoader(async (ids) => {
    return ids.map((id) => store.users.get(id) || null);
  });

  const postById = new DataLoader(async (ids) => {
    return ids.map((id) => store.posts.get(id) || null);
  });

  const commentById = new DataLoader(async (ids) => {
    return ids.map((id) => store.comments.get(id) || null);
  });

  const postsByUserId = new DataLoader(async (userIds) => {
    return userIds.map((userId) => {
      const ids = store.userPostIds.get(userId) || [];
      const items = ids.map((pid) => store.posts.get(pid)).filter(Boolean);
      return stableSortByCreatedAtDesc(items);
    });
  });

  const commentsByPostId = new DataLoader(async (postIds) => {
    return postIds.map((postId) => {
      const ids = store.postCommentIds.get(postId) || [];
      const items = ids.map((cid) => store.comments.get(cid)).filter(Boolean);
      return stableSortByCreatedAtDesc(items);
    });
  });

  return {
    userById,
    postById,
    commentById,
    postsByUserId,
    commentsByPostId,
  };
}

async function main() {
  const { ApolloServer } = await import('@apollo/server');
  const { startStandaloneServer } = await import('@apollo/server/standalone');
  const DataLoader = (await import('dataloader')).default;

  const store = makeStore();

  const typeDefs = /* GraphQL */ `
    scalar DateTime

    type Query {
      me: User
      user(id: ID!): User
      users(first: Int, after: ID): [User!]!
      post(id: ID!): Post
      posts(first: Int, after: ID): [Post!]!
      comment(id: ID!): Comment
      comments(first: Int, after: ID): [Comment!]!
    }

    type Mutation {
      createUser(handle: String!, displayName: String): User!
      createPost(userId: ID!, body: String!): Post!
      createComment(postId: ID!, userId: ID!, body: String!): Comment!
    }

    type User {
      id: ID!
      handle: String!
      displayName: String
      createdAt: DateTime!
      posts(first: Int, after: ID): [Post!]!
    }

    type Post {
      id: ID!
      body: String!
      createdAt: DateTime!
      user: User!
      comments(first: Int, after: ID): [Comment!]!
    }

    type Comment {
      id: ID!
      body: String!
      createdAt: DateTime!
      user: User!
      post: Post!
    }
  `;

  const resolvers = {
    DateTime: {
      serialize(value) {
        if (value instanceof Date) return value.toISOString();
        if (typeof value === 'string') return value;
        return new Date(value).toISOString();
      },
      parseValue(value) {
        return new Date(value);
      },
    },
    Query: {
      me: async (_parent, _args, ctx) => {
        const firstUser = stableSortByCreatedAtDesc(Array.from(ctx.store.users.values()))[0] || null;
        return firstUser;
      },
      user: async (_parent, { id }, ctx) => ctx.loaders.userById.load(id),
      users: async (_parent, { first, after }, ctx) => {
        const all = stableSortByCreatedAtDesc(Array.from(ctx.store.users.values()));
        return take(all, first, after);
      },
      post: async (_parent, { id }, ctx) => ctx.loaders.postById.load(id),
      posts: async (_parent, { first, after }, ctx) => {
        const all = stableSortByCreatedAtDesc(Array.from(ctx.store.posts.values()));
        return take(all, first, after);
      },
      comment: async (_parent, { id }, ctx) => ctx.loaders.commentById.load(id),
      comments: async (_parent, { first, after }, ctx) => {
        const all = stableSortByCreatedAtDesc(Array.from(ctx.store.comments.values()));
        return take(all, first, after);
      },
    },
    Mutation: {
      createUser: async (_parent, { handle, displayName }, ctx) => {
        const normalizedHandle = String(handle || '').trim();
        if (!normalizedHandle) throw new Error('handle_required');
        for (const u of ctx.store.users.values()) {
          if (u.handle.toLowerCase() === normalizedHandle.toLowerCase()) throw new Error('handle_taken');
        }
        const user = {
          id: id('usr'),
          handle: normalizedHandle,
          displayName: displayName == null ? null : String(displayName),
          createdAt: nowIso(),
        };
        ctx.store.addUser(user);
        ctx.loaders.userById.clear(user.id);
        return user;
      },
      createPost: async (_parent, { userId, body }, ctx) => {
        const u = await ctx.loaders.userById.load(userId);
        if (!u) throw new Error('user_not_found');
        const content = String(body || '').trim();
        if (!content) throw new Error('body_required');
        const post = { id: id('pst'), userId, body: content, createdAt: nowIso() };
        ctx.store.addPost(post);
        ctx.loaders.postById.clear(post.id);
        ctx.loaders.postsByUserId.clear(userId);
        return post;
      },
      createComment: async (_parent, { postId, userId, body }, ctx) => {
        const [p, u] = await Promise.all([
          ctx.loaders.postById.load(postId),
          ctx.loaders.userById.load(userId),
        ]);
        if (!p) throw new Error('post_not_found');
        if (!u) throw new Error('user_not_found');
        const content = String(body || '').trim();
        if (!content) throw new Error('body_required');
        const comment = { id: id('cmt'), postId, userId, body: content, createdAt: nowIso() };
        ctx.store.addComment(comment);
        ctx.loaders.commentById.clear(comment.id);
        ctx.loaders.commentsByPostId.clear(postId);
        return comment;
      },
    },
    User: {
      posts: async (parent, { first, after }, ctx) => {
        const all = await ctx.loaders.postsByUserId.load(parent.id);
        return take(all, first, after);
      },
    },
    Post: {
      user: async (parent, _args, ctx) => ctx.loaders.userById.load(parent.userId),
      comments: async (parent, { first, after }, ctx) => {
        const all = await ctx.loaders.commentsByPostId.load(parent.id);
        return take(all, first, after);
      },
    },
    Comment: {
      user: async (parent, _args, ctx) => ctx.loaders.userById.load(parent.userId),
      post: async (parent, _args, ctx) => ctx.loaders.postById.load(parent.postId),
    },
  };

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    formatError(formattedError, error) {
      const code = error?.message || formattedError.message;
      return {
        message: formattedError.message,
        path: formattedError.path,
        extensions: {
          ...formattedError.extensions,
          code,
        },
      };
    },
  });

  const port = Number.parseInt(process.env.PORT || '4000', 10);
  const host = process.env.HOST || '0.0.0.0';

  const { url } = await startStandaloneServer(server, {
    listen: { port, host },
    context: async () => {
      const loaders = createLoaders(DataLoader, store);
      return { store, loaders };
    },
  });

  console.log(`GraphQL API ready at ${url}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});