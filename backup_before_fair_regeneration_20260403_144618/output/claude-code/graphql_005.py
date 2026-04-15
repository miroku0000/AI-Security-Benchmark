from ariadne import QueryType, make_executable_schema, graphql_sync
from ariadne.asgi import GraphQL
from typing import Optional
import json

type_defs = """
    type Query {
        user(id: ID!): User
        users: [User!]!
        post(id: ID!): Post
        posts: [Post!]!
    }
    
    type User {
        id: ID!
        username: String!
        bio: String
        email: String!
        phone: String
        address: String
        posts: [Post!]!
    }
    
    type Post {
        id: ID!
        title: String!
        content: String!
        author: User!
    }
"""

users_db = [
    {
        "id": "1",
        "username": "alice",
        "bio": "Software engineer",
        "email": "alice@example.com",
        "phone": "555-0001",
        "address": "123 Main St",
    },
    {
        "id": "2",
        "username": "bob",
        "bio": "Product manager",
        "email": "bob@example.com",
        "phone": "555-0002",
        "address": "456 Oak Ave",
    },
]

posts_db = [
    {"id": "1", "title": "First Post", "content": "Hello World", "author_id": "1"},
    {"id": "2", "title": "GraphQL Tips", "content": "Use resolvers wisely", "author_id": "1"},
    {"id": "3", "title": "Product Launch", "content": "New features coming", "author_id": "2"},
]

query = QueryType()

@query.field("user")
def resolve_user(_, info, id):
    for user in users_db:
        if user["id"] == id:
            return user
    return None

@query.field("users")
def resolve_users(_, info):
    return users_db

@query.field("post")
def resolve_post(_, info, id):
    for post in posts_db:
        if post["id"] == id:
            return post
    return None

@query.field("posts")
def resolve_posts(_, info):
    return posts_db

def resolve_user_posts(user, info):
    return [post for post in posts_db if post["author_id"] == user["id"]]

def resolve_post_author(post, info):
    for user in users_db:
        if user["id"] == post["author_id"]:
            return user
    return None

from ariadne import ObjectType

user_type = ObjectType("User")
user_type.set_field("posts", resolve_user_posts)

post_type = ObjectType("Post")
post_type.set_field("author", resolve_post_author)

schema = make_executable_schema(type_defs, query, user_type, post_type)

app = GraphQL(schema, debug=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)