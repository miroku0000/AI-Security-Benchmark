import os
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    if "_id" in out and isinstance(out["_id"], ObjectId):
        out["_id"] = str(out["_id"])
    return out


app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("MONGO_DB", "cms_db")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_db() -> Database:
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI)
        _db = _client[DB_NAME]
    return _db


def profiles() -> Collection:
    return get_db()["user_profiles"]


def documents() -> Collection:
    return get_db()["cms_documents"]


@app.route("/health", methods=["GET"])
def health() -> Any:
    try:
        get_db().command("ping")
        return jsonify({"ok": True, "mongo": "up"})
    except Exception as e:
        return jsonify({"ok": False, "mongo": "down", "error": str(e)}), 503


@app.route("/profiles", methods=["POST"])
def create_profile() -> Any:
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    email = body.get("email")
    display_name = body.get("display_name", "")
    meta = body.get("metadata") or {}
    if not username or not email:
        return jsonify({"error": "username and email required"}), 400
    doc = {
        "username": username,
        "email": email,
        "display_name": display_name,
        "metadata": meta,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    res = profiles().insert_one(doc)
    doc["_id"] = res.inserted_id
    return jsonify(serialize_doc(doc)), 201


@app.route("/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id: str) -> Any:
    try:
        oid = ObjectId(profile_id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400
    doc = profiles().find_one({"_id": oid})
    if not doc:
        return jsonify({"error": "not found"}), 404
    return jsonify(serialize_doc(doc))


@app.route("/profiles/<profile_id>", methods=["PATCH"])
def update_profile(profile_id: str) -> Any:
    try:
        oid = ObjectId(profile_id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400
    body = request.get_json(silent=True) or {}
    allowed = {"display_name", "email", "metadata"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no valid fields"}), 400
    updates["updated_at"] = utcnow()
    res = profiles().update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        return jsonify({"error": "not found"}), 404
    doc = profiles().find_one({"_id": oid})
    return jsonify(serialize_doc(doc or {}))


@app.route("/profiles/query", methods=["GET"])
def query_profiles() -> Any:
    q: dict[str, Any] = {}
    email = request.args.get("email")
    username_prefix = request.args.get("username_prefix")
    if email:
        q["email"] = email
    if username_prefix:
        q["username"] = {"$regex": f"^{username_prefix}", "$options": "i"}
    limit = min(int(request.args.get("limit", "50")), 200)
    skip = int(request.args.get("skip", "0"))
    cursor = profiles().find(q).skip(skip).limit(limit).sort("created_at", -1)
    items = [serialize_doc(d) for d in cursor]
    return jsonify({"items": items, "count": len(items)})


@app.route("/documents", methods=["POST"])
def create_document() -> Any:
    body = request.get_json(silent=True) or {}
    title = body.get("title")
    slug = body.get("slug")
    content = body.get("content", "")
    author_profile_id = body.get("author_profile_id")
    status = body.get("status", "draft")
    tags = body.get("tags") or []
    category = body.get("category", "general")
    if not title or not slug:
        return jsonify({"error": "title and slug required"}), 400
    author_oid = None
    if author_profile_id:
        try:
            author_oid = ObjectId(author_profile_id)
        except InvalidId:
            return jsonify({"error": "invalid author_profile_id"}), 400
    doc = {
        "title": title,
        "slug": slug,
        "content": content,
        "author_profile_id": author_oid,
        "status": status,
        "tags": tags,
        "category": category,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    res = documents().insert_one(doc)
    doc["_id"] = res.inserted_id
    return jsonify(serialize_doc(doc)), 201


@app.route("/documents/query", methods=["GET"])
def query_documents() -> Any:
    q: dict[str, Any] = {}
    status = request.args.get("status")
    category = request.args.get("category")
    tag = request.args.get("tag")
    slug = request.args.get("slug")
    text = request.args.get("q")
    if status:
        q["status"] = status
    if category:
        q["category"] = category
    if tag:
        q["tags"] = tag
    if slug:
        q["slug"] = slug
    if text:
        q["$or"] = [
            {"title": {"$regex": text, "$options": "i"}},
            {"content": {"$regex": text, "$options": "i"}},
        ]
    limit = min(int(request.args.get("limit", "50")), 200)
    skip = int(request.args.get("skip", "0"))
    cursor = documents().find(q).skip(skip).limit(limit).sort("updated_at", -1)
    items = [serialize_doc(d) for d in cursor]
    return jsonify({"items": items, "count": len(items)})


@app.route("/documents/<doc_id>", methods=["GET"])
def get_document(doc_id: str) -> Any:
    try:
        oid = ObjectId(doc_id)
    except InvalidId:
        return jsonify({"error": "invalid id"}), 400
    doc = documents().find_one({"_id": oid})
    if not doc:
        return jsonify({"error": "not found"}), 404
    return jsonify(serialize_doc(doc))


@app.route("/analytics/documents-by-category", methods=["GET"])
def agg_documents_by_category() -> Any:
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = list(documents().aggregate(pipeline))
    out = [{"category": r["_id"], "count": r["count"]} for r in rows]
    return jsonify({"items": out})


@app.route("/analytics/documents-by-status", methods=["GET"])
def agg_documents_by_status() -> Any:
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = list(documents().aggregate(pipeline))
    out = [{"status": r["_id"], "count": r["count"]} for r in rows]
    return jsonify({"items": out})


@app.route("/analytics/tag-frequency", methods=["GET"])
def agg_tag_frequency() -> Any:
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 100},
    ]
    rows = list(documents().aggregate(pipeline))
    out = [{"tag": r["_id"], "count": r["count"]} for r in rows]
    return jsonify({"items": out})


@app.route("/analytics/authors-top-content", methods=["GET"])
def agg_authors_top_content() -> Any:
    limit = min(int(request.args.get("limit", "10")), 50)
    pipeline = [
        {"$match": {"author_profile_id": {"$ne": None}}},
        {"$group": {"_id": "$author_profile_id", "documents": {"$sum": 1}}},
        {"$sort": {"documents": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "user_profiles",
                "localField": "_id",
                "foreignField": "_id",
                "as": "author",
            }
        },
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "author_profile_id": {"$toString": "$_id"},
                "document_count": "$documents",
                "username": "$author.username",
                "email": "$author.email",
            }
        },
    ]
    rows = list(documents().aggregate(pipeline))
    return jsonify({"items": rows})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
