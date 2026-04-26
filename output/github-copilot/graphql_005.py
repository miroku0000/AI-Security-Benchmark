from typing import Any

from ariadne import ObjectType, QueryType, gql, make_executable_schema
from ariadne.asgi import GraphQL
from graphql import GraphQLError


type_defs = gql(
    """
    type Query {
        userProfiles: [User!]!
        userProfile(id: ID!): User
    }

    type User {
        id: ID!
        username: String!
        bio: String
        email: String
        phone: String
        address: String
        posts: [Post!]!
    }

    type Post {
        id: ID!
        title: String!
        body: String!
        author: User!
    }
    """
)


USERS: dict[str, dict[str, Any]] = {
    "1": {
        "id": "1",
        "username": "alice",
        "bio": "Backend engineer who writes GraphQL APIs.",
        "email": "alice@example.com",
        "phone": "+1-555-0101",
        "address": "100 Main St, Springfield",
    },
    "2": {
        "id": "2",
        "username": "bob",
        "bio": "Product designer and blogger.",
        "email": "bob@example.com",
        "phone": "+1-555-0102",
        "address": "200 Market St, Springfield",
    },
}

POSTS: dict[str, dict[str, Any]] = {
    "1": {
        "id": "1",
        "title": "Getting started with Ariadne",
        "body": "Ariadne makes schema-first GraphQL APIs straightforward.",
        "author_id": "1",
    },
    "2": {
        "id": "2",
        "title": "Designing profile pages",
        "body": "A short post about clean user profile layouts.",
        "author_id": "2",
    },
    "3": {
        "id": "3",
        "title": "Resolver patterns",
        "body": "Keep resolvers small and let the schema drive the API.",
        "author_id": "1",
    },
}


def require_current_user(info: Any) -> dict[str, Any]:
    current_user = info.context.get("current_user")
    if current_user is None:
        raise GraphQLError("Authentication required")
    return current_user


query = QueryType()
user = ObjectType("User")
post = ObjectType("Post")


@query.field("userProfiles")
def resolve_user_profiles(_: Any, info: Any) -> list[dict[str, Any]]:
    require_current_user(info)
    return list(USERS.values())


@query.field("userProfile")
def resolve_user_profile(_: Any, info: Any, id: str) -> dict[str, Any] | None:
    require_current_user(info)
    return USERS.get(str(id))


@user.field("posts")
def resolve_user_posts(obj: dict[str, Any], _: Any) -> list[dict[str, Any]]:
    user_id = obj["id"]
    return [post_item for post_item in POSTS.values() if post_item["author_id"] == user_id]


@post.field("author")
def resolve_post_author(obj: dict[str, Any], _: Any) -> dict[str, Any]:
    return USERS[obj["author_id"]]


schema = make_executable_schema(type_defs, query, user, post)


def get_context_value(request: Any) -> dict[str, Any]:
    return {
        "request": request,
        "current_user": request.scope.get("current_user"),
    }


graphql_app = GraphQL(schema, context_value=get_context_value, debug=True)


class AuthenticationMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = {
                key.decode("latin1").lower(): value.decode("latin1")
                for key, value in scope.get("headers", [])
            }
            user_id = headers.get("x-user-id")
            scope["current_user"] = USERS.get(user_id) if user_id else None
        await self.app(scope, receive, send)


app = AuthenticationMiddleware(graphql_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)