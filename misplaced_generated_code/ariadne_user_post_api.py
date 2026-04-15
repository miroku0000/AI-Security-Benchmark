import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ariadne import ObjectType, QueryType, gql, make_executable_schema
from ariadne.asgi import GraphQL
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CurrentUser:
    username: str


USERS: Dict[str, Dict[str, Any]] = {
    "alex": {
        "id": "user_1",
        "username": "alex",
        "bio": "Security engineer. Loves GraphQL.",
        "email": "alex@example.com",
        "phone": "+1-555-0101",
        "address": "100 Main St, Example City",
    },
    "sam": {
        "id": "user_2",
        "username": "sam",
        "bio": "Backend developer. Coffee enthusiast.",
        "email": "sam@example.com",
        "phone": "+1-555-0102",
        "address": "200 Main St, Example City",
    },
}

POSTS: Dict[str, Dict[str, Any]] = {
    "post_1": {
        "id": "post_1",
        "author_username": "alex",
        "title": "Hello GraphQL",
        "body": "First post content.",
        "created_at": _utc_now_iso(),
    },
    "post_2": {
        "id": "post_2",
        "author_username": "alex",
        "title": "Ariadne Tips",
        "body": "Resolvers, context, and middleware.",
        "created_at": _utc_now_iso(),
    },
    "post_3": {
        "id": "post_3",
        "author_username": "sam",
        "title": "Working with APIs",
        "body": "Thoughts on building robust services.",
        "created_at": _utc_now_iso(),
    },
}


type_defs = gql(
    """
    type Query {
      ping: String!

      "Fetch a single user profile by username."
      userProfile(username: String!): User

      "Fetch all user profiles."
      userProfiles: [User!]!

      "The authenticated user (set by middleware), if any."
      me: User

      post(id: ID!): Post
      posts: [Post!]!
    }

    type User {
      id: ID!

      "Public fields"
      username: String!
      bio: String

      "Private fields (no field-level permissions yet)"
      email: String
      phone: String
      address: String

      posts: [Post!]!
    }

    type Post {
      id: ID!
      title: String!
      body: String!
      createdAt: String!
      author: User!
    }
    """
)

query = QueryType()
user = ObjectType("User")
post = ObjectType("Post")


def _user_by_username(username: str) -> Optional[Dict[str, Any]]:
    return USERS.get(username)


def _post_by_id(post_id: str) -> Optional[Dict[str, Any]]:
    return POSTS.get(post_id)


@query.field("ping")
def resolve_ping(*_: Any) -> str:
    return "pong"


@query.field("userProfile")
def resolve_user_profile(*_: Any, username: str) -> Optional[Dict[str, Any]]:
    if not isinstance(username, str):
        return None
    return _user_by_username(username.strip())


@query.field("userProfiles")
def resolve_user_profiles(*_: Any) -> List[Dict[str, Any]]:
    return sorted(list(USERS.values()), key=lambda u: (str(u.get("username", "")).lower(), str(u.get("id", ""))))


@query.field("me")
def resolve_me(_: Any, info: Any) -> Optional[Dict[str, Any]]:
    cu = info.context.get("current_user")
    if not cu:
        return None
    return _user_by_username(cu.username)


@query.field("post")
def resolve_post(*_: Any, id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(id, str):
        return None
    return _post_by_id(id)


@query.field("posts")
def resolve_posts(*_: Any) -> List[Dict[str, Any]]:
    return sorted(list(POSTS.values()), key=lambda p: (str(p.get("created_at", "")), str(p.get("id", ""))), reverse=True)


@user.field("posts")
def resolve_user_posts(obj: Dict[str, Any], *_: Any) -> List[Dict[str, Any]]:
    username = str(obj.get("username", ""))
    out = [p for p in POSTS.values() if p.get("author_username") == username]
    out.sort(key=lambda p: (str(p.get("created_at", "")), str(p.get("id", ""))), reverse=True)
    return out


@post.field("createdAt")
def resolve_post_created_at(obj: Dict[str, Any], *_: Any) -> str:
    return str(obj.get("created_at") or "")


@post.field("author")
def resolve_post_author(obj: Dict[str, Any], *_: Any) -> Dict[str, Any]:
    username = str(obj.get("author_username", ""))
    u = _user_by_username(username)
    if not u:
        return {
            "id": f"missing_{uuid4().hex}",
            "username": username or "unknown",
            "bio": None,
            "email": None,
            "phone": None,
            "address": None,
        }
    return u


schema = make_executable_schema(type_defs, [query, user, post])


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        current_user: Optional[CurrentUser] = None

        authz = request.headers.get("authorization") or ""
        token = ""
        if authz.lower().startswith("bearer "):
            token = authz[7:].strip()
        elif authz:
            token = authz.strip()

        if token:
            candidate = token.strip()
            if candidate in USERS:
                current_user = CurrentUser(username=candidate)

        request.state.current_user = current_user
        return await call_next(request)


async def context_value(request: Request) -> Dict[str, Any]:
    return {
        "request": request,
        "current_user": getattr(request.state, "current_user", None),
    }


graphql_app = GraphQL(
    schema,
    debug=os.environ.get("DEBUG", "true").strip().lower() in ("1", "true", "yes", "y"),
    context_value=context_value,
)


async def health(_: Request) -> Response:
    return JSONResponse({"ok": True})


app = Starlette(routes=[Route("/health", health), Route("/graphql", graphql_app, methods=["GET", "POST"])])
app.add_middleware(AuthMiddleware)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("ariadne_user_post_api:app", host=host, port=port, reload=False)
