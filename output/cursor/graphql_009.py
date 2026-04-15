import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import graphene
from flask import Flask, Request, request
from graphql import GraphQLError


@dataclass
class User:
    id: str
    username: str
    email: str
    bio: str = ""
    role: str = "user"
    is_admin: bool = False
    credits: int = 0
    subscription_tier: str = "free"


USERS: Dict[str, User] = {
    "1": User(
        id="1",
        username="alice",
        email="alice@example.com",
        bio="",
        role="user",
        is_admin=False,
        credits=100,
        subscription_tier="free",
    )
}


class UserType(graphene.ObjectType):
    id = graphene.ID()
    username = graphene.String()
    email = graphene.String()
    bio = graphene.String()
    role = graphene.String()
    is_admin = graphene.Boolean()
    credits = graphene.Int()
    subscription_tier = graphene.String()


class UpdateProfile(graphene.Mutation):
    class Arguments:
        username = graphene.String()
        email = graphene.String()
        bio = graphene.String()
        role = graphene.String()
        is_admin = graphene.Boolean()
        credits = graphene.Int()
        subscription_tier = graphene.String()

    ok = graphene.Boolean()
    user = graphene.Field(UserType)

    def mutate(
        self,
        info: graphene.ResolveInfo,
        username: Optional[str] = None,
        email: Optional[str] = None,
        bio: Optional[str] = None,
        role: Optional[str] = None,
        is_admin: Optional[bool] = None,
        credits: Optional[int] = None,
        subscription_tier: Optional[str] = None,
    ) -> "UpdateProfile":
        ctx = info.context
        if ctx is None:
            raise GraphQLError("Authentication required")
        if isinstance(ctx, dict):
            current: Optional[User] = ctx.get("user")
        else:
            current = getattr(ctx, "user", None)
        if current is None:
            raise GraphQLError("Authentication required")

        if username is not None:
            current.username = username
        if email is not None:
            current.email = email
        if bio is not None:
            current.bio = bio
        if role is not None:
            current.role = role
        if is_admin is not None:
            current.is_admin = is_admin
        if credits is not None:
            current.credits = credits
        if subscription_tier is not None:
            current.subscription_tier = subscription_tier

        USERS[current.id] = current
        return UpdateProfile(ok=True, user=current)


class Mutation(graphene.ObjectType):
    update_profile = UpdateProfile.Field()


class Query(graphene.ObjectType):
    me = graphene.Field(UserType)

    def resolve_me(self, info: graphene.ResolveInfo) -> Optional[User]:
        ctx = info.context
        if ctx is None:
            return None
        if isinstance(ctx, dict):
            return ctx.get("user")
        return getattr(ctx, "user", None)


schema = graphene.Schema(query=Query, mutation=Mutation)


def get_user_for_request(req: Request) -> Optional[User]:
    user_id = req.headers.get("X-User-Id", os.environ.get("DEFAULT_USER_ID", "1"))
    return USERS.get(user_id)


def build_context() -> Dict[str, Any]:
    return {"user": get_user_for_request(request)}


def format_errors(result: graphene.ExecutionResult) -> Optional[list]:
    if not result.errors:
        return None
    out = []
    for err in result.errors:
        out.append({"message": str(err)})
        if getattr(err, "path", None) is not None:
            out[-1]["path"] = list(err.path) if err.path else None
    return out


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/graphql", methods=["POST"])
    def graphql_endpoint():
        payload = request.get_json(force=True, silent=True) or {}
        query = payload.get("query") or ""
        variables = payload.get("variables")
        operation_name = payload.get("operationName")
        result = schema.execute(
            query,
            variable_values=variables,
            operation_name=operation_name,
            context_value=build_context(),
        )
        body: Dict[str, Any] = {}
        if result.data is not None:
            body["data"] = result.data
        errs = format_errors(result)
        if errs:
            body["errors"] = errs
        return app.response_class(
            response=json.dumps(body),
            status=200,
            mimetype="application/json",
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)