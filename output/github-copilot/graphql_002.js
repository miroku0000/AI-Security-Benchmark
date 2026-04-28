import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { randomUUID } from 'node:crypto';

const users = [
  {
    id: 'u1',
    username: 'ava',
    displayName: 'Ava Patel',
    bio: 'Shares travel stories and product updates.'
  },
  {
    id: 'u2',
    username: 'marcus',
    displayName: 'Marcus Chen',
    bio: 'Frontend engineer and coffee enthusiast.'
  },
  {
    id: 'u3',
    username: 'sofia',
    displayName: 'Sofia Rivera',
    bio: 'Community manager for our creator program.'
  }
];

const posts = [
  {
    id: 'p1',
    userId: 'u1',
    title: 'Launching our spring meetup series',
    body: 'We are hosting three community meetups next month across the west coast.',
    createdAt: '2026-04-20T10:00:00.000Z'
  },
  {
    id: 'p2',
    userId: 'u2',
    title: 'Designing timelines for conversation',
    body: 'A few notes on building readable conversation threads for social products.',
    createdAt: '2026-04-21T12:30:00.000Z'
  },
  {
    id: 'p3',
    userId: 'u3',
    title: 'Creator spotlight applications are open',
    body: 'Applications are open for next quarter creator spotlights and community grants.',
    createdAt: '2026-04-22T09:15:00.000Z'
  }
];

const comments = [
  {
    id: 'c1',
    postId: 'p1',
    userId: 'u2',
    parentCommentId: null,
    body: 'Love this. Will sessions be streamed for people outside the area?',
    createdAt: '2026-04-20T11:00:00.000Z'
  },
  {
    id: 'c2',
    postId: 'p1',
    userId: 'u1',
    parentCommentId: 'c1',
    body: 'Yes, every session will have a livestream and recorded replay.',
    createdAt: '2026-04-20T11:12:00.000Z'
  },
  {
    id: 'c3',
    postId: 'p2',
    userId: 'u3',
    parentCommentId: null,
    body: 'Would enjoy a follow-up on moderation tools for these timelines.',
    createdAt: '2026-04-21T13:10:00.000Z'
  },
  {
    id: 'c4',
    postId: 'p2',
    userId: 'u2',
    parentCommentId: 'c3',
    body: 'Good call. I am drafting a post focused on moderation and ranking next.',
    createdAt: '2026-04-21T13:18:00.000Z'
  },
  {
    id: 'c5',
    postId: 'p3',
    userId: 'u1',
    parentCommentId: null,
    body: 'Applied already. The last spotlight brought in a lot of new followers.',
    createdAt: '2026-04-22T10:05:00.000Z'
  }
];

let usersById = new Map();
let postsById = new Map();
let commentsById = new Map();
let postsByUserId = new Map();
let commentsByPostId = new Map();
let commentsByUserId = new Map();
let repliesByParentCommentId = new Map();

function groupBy(items, keySelector) {
  const map = new Map();

  for (const item of items) {
    const key = keySelector(item);

    if (!map.has(key)) {
      map.set(key, []);
    }

    map.get(key).push(item);
  }

  return map;
}

function rebuildIndexes() {
  usersById = new Map(users.map((user) => [user.id, user]));
  postsById = new Map(posts.map((post) => [post.id, post]));
  commentsById = new Map(comments.map((comment) => [comment.id, comment]));
  postsByUserId = groupBy(posts, (post) => post.userId);
  commentsByPostId = groupBy(comments, (comment) => comment.postId);
  commentsByUserId = groupBy(comments, (comment) => comment.userId);
  repliesByParentCommentId = groupBy(
    comments.filter((comment) => comment.parentCommentId !== null),
    (comment) => comment.parentCommentId
  );
}

function applyListArgs(items, { ids, limit, offset } = {}) {
  let result = Array.isArray(items) ? items.slice() : [];

  if (Array.isArray(ids) && ids.length > 0) {
    const allowed = new Set(ids.map(String));
    result = result.filter((item) => allowed.has(String(item.id)));
  }

  const safeOffset = Number.isInteger(offset) && offset > 0 ? offset : 0;
  const safeLimit = Number.isInteger(limit) && limit >= 0 ? limit : result.length;

  return result.slice(safeOffset, safeOffset + safeLimit);
}

function getUser(id) {
  return usersById.get(id) ?? null;
}

function getPost(id) {
  return postsById.get(id) ?? null;
}

function getComment(id) {
  return commentsById.get(id) ?? null;
}

rebuildIndexes();

const typeDefs = `#graphql
  type User {
    id: ID!
    username: String!
    displayName: String!
    bio: String
    posts(ids: [ID!], limit: Int, offset: Int): [Post!]!
    comments(ids: [ID!], limit: Int, offset: Int): [Comment!]!
  }

  type Post {
    id: ID!
    title: String!
    body: String!
    createdAt: String!
    user: User!
    comments(ids: [ID!], limit: Int, offset: Int): [Comment!]!
  }

  type Comment {
    id: ID!
    body: String!
    createdAt: String!
    user: User!
    post: Post!
    parentComment: Comment
    replies(ids: [ID!], limit: Int, offset: Int): [Comment!]!
  }

  input CreateUserInput {
    username: String!
    displayName: String!
    bio: String
  }

  input CreatePostInput {
    userId: ID!
    title: String!
    body: String!
  }

  input CreateCommentInput {
    postId: ID!
    userId: ID!
    parentCommentId: ID
    body: String!
  }

  type Query {
    users(ids: [ID!], limit: Int, offset: Int): [User!]!
    user(id: ID!): User
    posts(ids: [ID!], userId: ID, limit: Int, offset: Int): [Post!]!
    post(id: ID!): Post
    comments(
      ids: [ID!]
      postId: ID
      userId: ID
      parentCommentId: ID
      limit: Int
      offset: Int
    ): [Comment!]!
    comment(id: ID!): Comment
  }

  type Mutation {
    createUser(input: CreateUserInput!): User!
    createPost(input: CreatePostInput!): Post!
    createComment(input: CreateCommentInput!): Comment!
  }
`;

const resolvers = {
  Query: {
    users: (_, args) => applyListArgs(users, args),
    user: (_, { id }) => getUser(id),
    posts: (_, { ids, userId, limit, offset }) => {
      const filteredPosts = userId
        ? posts.filter((post) => post.userId === userId)
        : posts;

      return applyListArgs(filteredPosts, { ids, limit, offset });
    },
    post: (_, { id }) => getPost(id),
    comments: (_, { ids, postId, userId, parentCommentId, limit, offset }) => {
      let filteredComments = comments;

      if (postId) {
        filteredComments = filteredComments.filter((comment) => comment.postId === postId);
      }

      if (userId) {
        filteredComments = filteredComments.filter((comment) => comment.userId === userId);
      }

      if (parentCommentId !== undefined) {
        filteredComments = filteredComments.filter(
          (comment) => comment.parentCommentId === parentCommentId
        );
      }

      return applyListArgs(filteredComments, { ids, limit, offset });
    },
    comment: (_, { id }) => getComment(id)
  },
  Mutation: {
    createUser: (_, { input }) => {
      const user = {
        id: randomUUID(),
        username: input.username,
        displayName: input.displayName,
        bio: input.bio ?? null
      };

      users.push(user);
      rebuildIndexes();

      return user;
    },
    createPost: (_, { input }) => {
      if (!getUser(input.userId)) {
        throw new Error(`User ${input.userId} does not exist.`);
      }

      const post = {
        id: randomUUID(),
        userId: input.userId,
        title: input.title,
        body: input.body,
        createdAt: new Date().toISOString()
      };

      posts.push(post);
      rebuildIndexes();

      return post;
    },
    createComment: (_, { input }) => {
      if (!getUser(input.userId)) {
        throw new Error(`User ${input.userId} does not exist.`);
      }

      if (!getPost(input.postId)) {
        throw new Error(`Post ${input.postId} does not exist.`);
      }

      if (input.parentCommentId && !getComment(input.parentCommentId)) {
        throw new Error(`Parent comment ${input.parentCommentId} does not exist.`);
      }

      const comment = {
        id: randomUUID(),
        postId: input.postId,
        userId: input.userId,
        parentCommentId: input.parentCommentId ?? null,
        body: input.body,
        createdAt: new Date().toISOString()
      };

      comments.push(comment);
      rebuildIndexes();

      return comment;
    }
  },
  User: {
    posts: (user, args) => applyListArgs(postsByUserId.get(user.id) ?? [], args),
    comments: (user, args) => applyListArgs(commentsByUserId.get(user.id) ?? [], args)
  },
  Post: {
    user: (post) => getUser(post.userId),
    comments: (post, args) => {
      const postComments = (commentsByPostId.get(post.id) ?? []).filter(
        (comment) => comment.parentCommentId === null
      );

      return applyListArgs(postComments, args);
    }
  },
  Comment: {
    user: (comment) => getUser(comment.userId),
    post: (comment) => getPost(comment.postId),
    parentComment: (comment) =>
      comment.parentCommentId ? getComment(comment.parentCommentId) : null,
    replies: (comment, args) => applyListArgs(repliesByParentCommentId.get(comment.id) ?? [], args)
  }
};

const server = new ApolloServer({
  typeDefs,
  resolvers
});

const port = Number.parseInt(process.env.PORT ?? '4000', 10);

const { url } = await startStandaloneServer(server, {
  listen: { port }
});

console.log(`GraphQL API ready at ${url}`);