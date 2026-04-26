#!/usr/bin/env python3
import os
import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("MONGO_DB_NAME", "content_management_system")

PROFILE_FIELDS = {
    "user_id",
    "email",
    "display_name",
    "bio",
    "roles",
    "preferences",
    "avatar_url",
    "social_links",
    "metadata",
}

DOCUMENT_FIELDS = {
    "title",
    "slug",
    "author_id",
    "content",
    "summary",
    "tags",
    "category",
    "status",
    "metadata",
    "view_count",
    "published_at",
}

SORT_FIELDS = {
    "created_at",
    "updated_at",
    "published_at",
    "title",
    "view_count",
    "status",
    "category",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    return value


def json_response(payload: Any, status_code: int = 200):
    return jsonify(serialize_value(payload)), status_code


def error_response(message: str, status_code: int):
    return json_response({"error": message}, status_code)


def parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise ValueError("Invalid document id.") from exc


def parse_json_body() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


def parse_iso_datetime(value: Any, field_name: str) -> datetime:
    if value is None:
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO 8601 string.")
    normalized_value = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO 8601 string.") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "document"


def normalize_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError(f"{field_name} must be a string or an array of strings.")


def pick_fields(payload: dict[str, Any], allowed_fields: set[str]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key in allowed_fields}


def create_app() -> Flask:
    app = Flask(__name__)

    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    database = mongo_client[DATABASE_NAME]
    indexes_ready = False

    def ensure_indexes() -> None:
        nonlocal indexes_ready
        if indexes_ready:
            return
        profiles = database.user_profiles
        documents = database.documents
        profiles.create_index("user_id", unique=True)
        profiles.create_index("email", unique=True)
        documents.create_index("slug", unique=True, sparse=True)
        documents.create_index([("author_id", ASCENDING), ("status", ASCENDING)])
        documents.create_index([("category", ASCENDING), ("created_at", DESCENDING)])
        documents.create_index("tags")
        documents.create_index(
            [("title", "text"), ("content", "text"), ("summary", "text"), ("tags", "text"), ("category", "text")]
        )
        indexes_ready = True

    def get_profiles_collection():
        ensure_indexes()
        return database.user_profiles

    def get_documents_collection():
        ensure_indexes()
        return database.documents

    @app.get("/health")
    def healthcheck():
        mongo_client.admin.command("ping")
        return json_response({"status": "ok", "database": DATABASE_NAME})

    @app.post("/profiles")
    def create_profile():
        profiles = get_profiles_collection()
        payload = parse_json_body()
        profile = pick_fields(payload, PROFILE_FIELDS)

        if not profile.get("user_id"):
            return error_response("user_id is required.", 400)
        if not profile.get("email"):
            return error_response("email is required.", 400)

        if "roles" in profile:
            profile["roles"] = normalize_string_list(profile["roles"], "roles")

        now = utcnow()
        profile["created_at"] = now
        profile["updated_at"] = now

        try:
            profiles.insert_one(profile)
        except DuplicateKeyError:
            return error_response("A profile with that user_id or email already exists.", 409)

        created_profile = profiles.find_one({"user_id": profile["user_id"]})
        return json_response(created_profile, 201)

    @app.get("/profiles/<user_id>")
    def get_profile(user_id: str):
        profiles = get_profiles_collection()
        profile = profiles.find_one({"user_id": user_id})
        if profile is None:
            return error_response("Profile not found.", 404)
        return json_response(profile)

    @app.put("/profiles/<user_id>")
    def upsert_profile(user_id: str):
        profiles = get_profiles_collection()
        payload = parse_json_body()
        updates = pick_fields(payload, PROFILE_FIELDS - {"user_id"})

        if not updates:
            return error_response("No valid profile fields provided.", 400)

        existing_profile = profiles.find_one({"user_id": user_id}, {"_id": 1, "email": 1})
        if existing_profile is None and not updates.get("email"):
            return error_response("email is required when creating a new profile.", 400)

        if "roles" in updates:
            updates["roles"] = normalize_string_list(updates["roles"], "roles")

        updates["updated_at"] = utcnow()

        try:
            profile = profiles.find_one_and_update(
                {"user_id": user_id},
                {
                    "$set": updates,
                    "$setOnInsert": {"user_id": user_id, "created_at": utcnow()},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            return error_response("A profile with that email already exists.", 409)

        return json_response(profile)

    @app.post("/documents")
    def create_document():
        documents = get_documents_collection()
        payload = parse_json_body()
        document = pick_fields(payload, DOCUMENT_FIELDS)

        if not document.get("title"):
            return error_response("title is required.", 400)
        if not document.get("author_id"):
            return error_response("author_id is required.", 400)
        if not document.get("content"):
            return error_response("content is required.", 400)

        if "published_at" in document:
            document["published_at"] = parse_iso_datetime(document["published_at"], "published_at")

        document["slug"] = document.get("slug") or slugify(document["title"])
        document["status"] = document.get("status", "draft")
        document["tags"] = normalize_string_list(document.get("tags"), "tags")
        document["view_count"] = int(document.get("view_count", 0))

        now = utcnow()
        document["created_at"] = now
        document["updated_at"] = now

        try:
            result = documents.insert_one(document)
        except DuplicateKeyError:
            return error_response("A document with that slug already exists.", 409)

        created_document = documents.find_one({"_id": result.inserted_id})
        return json_response(created_document, 201)

    @app.get("/documents/<document_id>")
    def get_document(document_id: str):
        documents = get_documents_collection()
        object_id = parse_object_id(document_id)
        document = documents.find_one({"_id": object_id})
        if document is None:
            return error_response("Document not found.", 404)
        return json_response(document)

    @app.put("/documents/<document_id>")
    def update_document(document_id: str):
        documents = get_documents_collection()
        object_id = parse_object_id(document_id)
        payload = parse_json_body()
        updates = pick_fields(payload, DOCUMENT_FIELDS)

        if not updates:
            return error_response("No valid document fields provided.", 400)

        if "published_at" in updates:
            updates["published_at"] = parse_iso_datetime(updates["published_at"], "published_at")
        if "title" in updates and "slug" not in updates:
            updates["slug"] = slugify(updates["title"])
        if "tags" in updates:
            updates["tags"] = normalize_string_list(updates["tags"], "tags")
        if "view_count" in updates:
            updates["view_count"] = int(updates["view_count"])
        updates["updated_at"] = utcnow()

        try:
            document = documents.find_one_and_update(
                {"_id": object_id},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            return error_response("A document with that slug already exists.", 409)

        if document is None:
            return error_response("Document not found.", 404)
        return json_response(document)

    @app.delete("/documents/<document_id>")
    def delete_document(document_id: str):
        documents = get_documents_collection()
        object_id = parse_object_id(document_id)
        deleted = documents.find_one_and_delete({"_id": object_id})
        if deleted is None:
            return error_response("Document not found.", 404)
        return json_response({"deleted": True, "document_id": document_id})

    @app.get("/documents")
    def list_documents():
        documents = get_documents_collection()
        query: dict[str, Any] = {}

        if request.args.get("author_id"):
            query["author_id"] = request.args["author_id"]
        if request.args.get("status"):
            query["status"] = request.args["status"]
        if request.args.get("category"):
            query["category"] = request.args["category"]
        if request.args.get("tag"):
            query["tags"] = request.args["tag"]
        if request.args.get("q"):
            query["$text"] = {"$search": request.args["q"]}

        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        skip = max(int(request.args.get("skip", 0)), 0)
        sort_by = request.args.get("sort_by", "created_at")
        sort_dir = DESCENDING if request.args.get("sort_dir", "desc").lower() == "desc" else ASCENDING

        if sort_by not in SORT_FIELDS:
            return error_response(f"sort_by must be one of: {', '.join(sorted(SORT_FIELDS))}.", 400)

        cursor = documents.find(query)
        if "$text" in query:
            cursor = cursor.sort([("score", {"$meta": "textScore"})])
        else:
            cursor = cursor.sort(sort_by, sort_dir)

        results = list(cursor.skip(skip).limit(limit))
        total = documents.count_documents(query)
        return json_response({"items": results, "count": len(results), "total": total, "limit": limit, "skip": skip})

    @app.post("/documents/query")
    def query_documents():
        documents = get_documents_collection()
        payload = parse_json_body()
        filters = payload.get("filters", {})
        if filters is None:
            filters = {}
        if not isinstance(filters, dict):
            return error_response("filters must be a JSON object.", 400)

        query: dict[str, Any] = {}

        for field in ("author_id", "status", "category", "slug"):
            if filters.get(field) is not None:
                query[field] = filters[field]

        if filters.get("tags"):
            tags = normalize_string_list(filters["tags"], "tags")
            query["tags"] = {"$all": tags}
        if filters.get("title_contains"):
            query["title"] = {"$regex": re.escape(filters["title_contains"]), "$options": "i"}
        if filters.get("content_contains"):
            query["content"] = {"$regex": re.escape(filters["content_contains"]), "$options": "i"}
        if filters.get("created_after") or filters.get("created_before"):
            query["created_at"] = {}
            if filters.get("created_after"):
                query["created_at"]["$gte"] = parse_iso_datetime(filters["created_after"], "created_after")
            if filters.get("created_before"):
                query["created_at"]["$lte"] = parse_iso_datetime(filters["created_before"], "created_before")
        if filters.get("q"):
            query["$text"] = {"$search": filters["q"]}

        projection = payload.get("projection")
        if projection is not None:
            if not isinstance(projection, list) or not all(isinstance(item, str) for item in projection):
                return error_response("projection must be an array of field names.", 400)
            projection = {field: 1 for field in projection}

        limit = min(max(int(payload.get("limit", 20)), 1), 100)
        skip = max(int(payload.get("skip", 0)), 0)
        sort_by = payload.get("sort_by", "created_at")
        sort_dir = DESCENDING if str(payload.get("sort_dir", "desc")).lower() == "desc" else ASCENDING

        if sort_by not in SORT_FIELDS:
            return error_response(f"sort_by must be one of: {', '.join(sorted(SORT_FIELDS))}.", 400)

        cursor = documents.find(query, projection)
        if "$text" in query:
            cursor = cursor.sort([("score", {"$meta": "textScore"})])
        else:
            cursor = cursor.sort(sort_by, sort_dir)

        results = list(cursor.skip(skip).limit(limit))
        total = documents.count_documents(query)
        return json_response({"items": results, "count": len(results), "total": total, "limit": limit, "skip": skip})

    @app.get("/analytics/documents/overview")
    def documents_overview():
        documents = get_documents_collection()
        match_stage: dict[str, Any] = {}

        for field in ("author_id", "status", "category"):
            if request.args.get(field):
                match_stage[field] = request.args[field]

        pipeline: list[dict[str, Any]] = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.append(
            {
                "$facet": {
                    "summary": [
                        {
                            "$group": {
                                "_id": None,
                                "total_documents": {"$sum": 1},
                                "published_documents": {
                                    "$sum": {"$cond": [{"$eq": ["$status", "published"]}, 1, 0]}
                                },
                                "draft_documents": {
                                    "$sum": {"$cond": [{"$eq": ["$status", "draft"]}, 1, 0]}
                                },
                                "total_views": {"$sum": {"$ifNull": ["$view_count", 0]}},
                                "average_views": {"$avg": {"$ifNull": ["$view_count", 0]}},
                            }
                        }
                    ],
                    "by_status": [
                        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1, "_id": 1}},
                    ],
                    "by_category": [
                        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1, "_id": 1}},
                    ],
                    "top_tags": [
                        {"$unwind": "$tags"},
                        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1, "_id": 1}},
                        {"$limit": 10},
                    ],
                    "top_authors": [
                        {
                            "$group": {
                                "_id": "$author_id",
                                "document_count": {"$sum": 1},
                                "total_views": {"$sum": {"$ifNull": ["$view_count", 0]}},
                            }
                        },
                        {"$sort": {"document_count": -1, "total_views": -1, "_id": 1}},
                        {"$limit": 10},
                    ],
                }
            }
        )

        result = list(documents.aggregate(pipeline))
        overview = result[0] if result else {}
        overview["summary"] = overview.get("summary", [{}])[0] if overview.get("summary") else {}
        return json_response(overview)

    @app.post("/analytics/documents/group-by")
    def group_documents():
        documents = get_documents_collection()
        payload = parse_json_body()
        group_by = payload.get("group_by", "category")

        if group_by not in {"status", "category", "author_id"}:
            return error_response("group_by must be one of: status, category, author_id.", 400)

        filters = payload.get("filters", {})
        if filters is None:
            filters = {}
        if not isinstance(filters, dict):
            return error_response("filters must be a JSON object.", 400)

        match_stage = {key: value for key, value in filters.items() if key in {"author_id", "status", "category"}}
        pipeline: list[dict[str, Any]] = []

        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": f"${group_by}",
                        "document_count": {"$sum": 1},
                        "total_views": {"$sum": {"$ifNull": ["$view_count", 0]}},
                        "average_views": {"$avg": {"$ifNull": ["$view_count", 0]}},
                    }
                },
                {"$sort": {"document_count": -1, "_id": 1}},
            ]
        )

        return json_response({"group_by": group_by, "results": list(documents.aggregate(pipeline))})

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        return error_response(str(error), 400)

    @app.errorhandler(PyMongoError)
    def handle_mongo_error(_: PyMongoError):
        return error_response("MongoDB operation failed.", 503)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )