from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Dict, Optional

import graphene
from flask import Flask, jsonify, request

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_ROLES = {"user", "manager", "support", "admin"}
ALLOWED_SUBSCRIPTION_TIERS = {"free", "pro", "enterprise"}


@dataclass
class User:
    id: int
    username: str
    email: str
    bio: str
    role: str
    is_admin: bool
    credits: int
    subscription_tier: str


USER_LOCK = threading.Lock()
USERS: Dict[int, User] = {
    1: User(
        id=1,
        username="admin",
        email="admin@example.com",
        bio="System administrator",
        role="admin",
        is_admin=True,
        credits=1000,
        subscription_tier="enterprise",
    ),
    2: User(
        id=2,
        username="alice",
        email="alice@example.com",
        bio="Product tester",
        role="user",
        is_admin=False,
        credits=50,
        subscription_tier="free",
    ),
}


class UserType(graphene.ObjectType):
    id = graphene.ID(required=True)
    username = graphene.String(required=True)
    email = graphene.String(required=True)
    bio = graphene.String(required=True)
    role = graphene.String(required=True)
    is_admin = graphene.Boolean(required=True)
    credits = graphene.Int(required=True)
    subscription_tier = graphene.String(required=True)


class UpdateUserProfileInput(graphene.InputObjectType):
    username = graphene.String()
    email = graphene.String()
    bio = graphene.String()
    role = graphene.String()
    is_admin = graphene.Boolean()
    credits = graphene.Int()
    subscription_tier = graphene.String()


def get_current_user() -> Optional[User]:
    raw_user_id = request.headers.get("X-User-Id")
    if not raw_user_id:
        return None
    try:
        user_id = int(raw_user_id)
    except ValueError:
        return None
    return USERS.get(user_id)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_username(username: str) -> Optional[str]:
    if not USERNAME_RE.fullmatch(username):
        return "username must be 3-30 characters and contain only letters, numbers, or underscores"
    return None


def validate_email(email: str) -> Optional[str]:
    if not EMAIL_RE.fullmatch(email):
        return "email must be a valid email address"
    return None


def validate_role(role: str) -> Optional[str]:
    if role not in ALLOWED_ROLES:
        return f"role must be one of: {', '.join(sorted(ALLOWED_ROLES))}"
    return None


def validate_subscription_tier(subscription_tier: str) -> Optional[str]:
    if subscription_tier not in ALLOWED_SUBSCRIPTION_TIERS:
        return f"subscription_tier must be one of: {', '.join(sorted(ALLOWED_SUBSCRIPTION_TIERS))}"
    return None


def find_user_by_username(username: str) -> Optional[User]:
    for user in USERS.values():
        if user.username.lower() == username.lower():
            return user
    return None


def find_user_by_email(email: str) -> Optional[User]:
    normalized = normalize_email(email)
    for user in USERS.values():
        if normalize_email(user.email) == normalized:
            return user
    return None


class UpdateUserProfile(graphene.Mutation):
    class Arguments:
        input = UpdateUserProfileInput(required=True)
        user_id = graphene.ID()

    ok = graphene.Boolean(required=True)
    user = graphene.Field(UserType)
    errors = graphene.List(graphene.NonNull(graphene.String), required=True)

    @staticmethod
    def mutate(root, info, input, user_id=None):
        current_user = info.context.get("current_user")
        if current_user is None:
            return UpdateUserProfile(ok=False, user=None, errors=["authentication required"])

        target_user_id = current_user.id
        if user_id is not None:
            try:
                target_user_id = int(user_id)
            except (TypeError, ValueError):
                return UpdateUserProfile(ok=False, user=None, errors=["user_id must be a valid integer"])

        target_user = USERS.get(target_user_id)
        if target_user is None:
            return UpdateUserProfile(ok=False, user=None, errors=["target user not found"])

        if target_user.id != current_user.id and not current_user.is_admin:
            return UpdateUserProfile(
                ok=False,
                user=None,
                errors=["not authorized to update another user's profile"],
            )

        errors = []
        updates = {}

        if input.username is not None:
            username = input.username.strip()
            error = validate_username(username)
            if error:
                errors.append(error)
            else:
                existing = find_user_by_username(username)
                if existing and existing.id != target_user.id:
                    errors.append("username is already taken")
                else:
                    updates["username"] = username

        if input.email is not None:
            email = input.email.strip()
            error = validate_email(email)
            if error:
                errors.append(error)
            else:
                existing = find_user_by_email(email)
                if existing and existing.id != target_user.id:
                    errors.append("email is already in use")
                else:
                    updates["email"] = email

        if input.bio is not None:
            bio = input.bio.strip()
            if len(bio) > 500:
                errors.append("bio must be 500 characters or fewer")
            else:
                updates["bio"] = bio

        privileged_fields_present = any(
            getattr(input, field_name) is not None
            for field_name in ("role", "is_admin", "credits", "subscription_tier")
        )

        if privileged_fields_present and not current_user.is_admin:
            errors.append("only admins can update role, is_admin, credits, or subscription_tier")

        if current_user.is_admin:
            if input.role is not None:
                role = input.role.strip()
                error = validate_role(role)
                if error:
                    errors.append(error)
                else:
                    updates["role"] = role

            if input.is_admin is not None:
                updates["is_admin"] = bool(input.is_admin)

            if input.credits is not None:
                if input.credits < 0:
                    errors.append("credits must be greater than or equal to 0")
                else:
                    updates["credits"] = int(input.credits)

            if input.subscription_tier is not None:
                subscription_tier = input.subscription_tier.strip()
                error = validate_subscription_tier(subscription_tier)
                if error:
                    errors.append(error)
                else:
                    updates["subscription_tier"] = subscription_tier

        if errors:
            return UpdateUserProfile(ok=False, user=None, errors=errors)

        with USER_LOCK:
            stored_user = USERS[target_user.id]
            for field_name, value in updates.items():
                setattr(stored_user, field_name, value)

        return UpdateUserProfile(ok=True, user=USERS[target_user.id], errors=[])


class Query(graphene.ObjectType):
    me = graphene.Field(UserType)
    user = graphene.Field(UserType, user_id=graphene.ID(required=True))
    users = graphene.List(graphene.NonNull(UserType))

    @staticmethod
    def resolve_me(root, info):
        return info.context.get("current_user")

    @staticmethod
    def resolve_user(root, info, user_id):
        current_user = info.context.get("current_user")
        if current_user is None:
            raise Exception("authentication required")

        try:
            target_user_id = int(user_id)
        except (TypeError, ValueError):
            raise Exception("user_id must be a valid integer")

        if current_user.id != target_user_id and not current_user.is_admin:
            raise Exception("not authorized to view another user's profile")

        return USERS.get(target_user_id)

    @staticmethod
    def resolve_users(root, info):
        current_user = info.context.get("current_user")
        if current_user is None or not current_user.is_admin:
            raise Exception("admin access required")
        return list(USERS.values())


class Mutation(graphene.ObjectType):
    update_user_profile = UpdateUserProfile.Field()


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(
        {
            "service": "user-management-graphql",
            "graphql_endpoint": "/graphql",
            "auth_header": "X-User-Id",
        }
    )


@app.post("/graphql")
def graphql_server():
    payload = request.get_json(silent=True) or {}
    query = payload.get("query")
    variables = payload.get("variables")
    operation_name = payload.get("operationName")

    if not query:
        return jsonify({"errors": [{"message": "request body must include 'query'"}]}), 400

    result = schema.execute(
        query,
        variable_values=variables,
        context_value={"request": request, "current_user": get_current_user()},
        operation_name=operation_name,
    )

    response = {}
    if result.errors:
        response["errors"] = [{"message": str(error)} for error in result.errors]
    if result.data is not None:
        response["data"] = result.data

    return jsonify(response), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)