from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)

client = MongoClient("mongodb://localhost:27017")
db = client.content_management
users_collection = db.users
documents_collection = db.documents


def serialize_doc(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    user = {
        "username": data["username"],
        "email": data["email"],
        "role": data.get("role", "viewer"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = users_collection.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return jsonify(user), 201


@app.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(serialize_doc(user))


@app.route("/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()
    data["updated_at"] = datetime.utcnow()
    result = users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": data},
    )
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    return jsonify(serialize_doc(user))


@app.route("/users", methods=["GET"])
def list_users():
    role = request.args.get("role")
    query = {}
    if role:
        query["role"] = role
    users = [serialize_doc(u) for u in users_collection.find(query)]
    return jsonify(users)


@app.route("/documents", methods=["POST"])
def create_document():
    data = request.get_json()
    doc = {
        "title": data["title"],
        "content": data["content"],
        "author_id": data["author_id"],
        "tags": data.get("tags", []),
        "status": data.get("status", "draft"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = documents_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return jsonify(doc), 201


@app.route("/documents/<doc_id>", methods=["GET"])
def get_document(doc_id):
    doc = documents_collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(serialize_doc(doc))


@app.route("/documents/<doc_id>", methods=["PUT"])
def update_document(doc_id):
    data = request.get_json()
    data["updated_at"] = datetime.utcnow()
    result = documents_collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": data},
    )
    if result.matched_count == 0:
        return jsonify({"error": "Document not found"}), 404
    doc = documents_collection.find_one({"_id": ObjectId(doc_id)})
    return jsonify(serialize_doc(doc))


@app.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    result = documents_collection.delete_one({"_id": ObjectId(doc_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Document not found"}), 404
    return jsonify({"message": "Document deleted"})


@app.route("/documents", methods=["GET"])
def query_documents():
    query = {}
    if request.args.get("author_id"):
        query["author_id"] = request.args["author_id"]
    if request.args.get("status"):
        query["status"] = request.args["status"]
    if request.args.get("tag"):
        query["tags"] = request.args["tag"]
    if request.args.get("search"):
        query["$or"] = [
            {"title": {"$regex": request.args["search"], "$options": "i"}},
            {"content": {"$regex": request.args["search"], "$options": "i"}},
        ]
    sort_field = request.args.get("sort", "created_at")
    sort_order = -1 if request.args.get("order", "desc") == "desc" else 1
    limit = int(request.args.get("limit", 20))
    skip = int(request.args.get("skip", 0))

    docs = documents_collection.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
    return jsonify([serialize_doc(d) for d in docs])


@app.route("/documents/stats/by-author", methods=["GET"])
def docs_by_author():
    pipeline = [
        {"$group": {
            "_id": "$author_id",
            "total_documents": {"$sum": 1},
            "statuses": {"$push": "$status"},
        }},
        {"$sort": {"total_documents": -1}},
    ]
    results = list(documents_collection.aggregate(pipeline))
    for r in results:
        r["author_id"] = r.pop("_id")
    return jsonify(results)


@app.route("/documents/stats/by-status", methods=["GET"])
def docs_by_status():
    pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "latest": {"$max": "$updated_at"},
        }},
        {"$sort": {"count": -1}},
    ]
    results = list(documents_collection.aggregate(pipeline))
    for r in results:
        r["status"] = r.pop("_id")
    return jsonify(results)


@app.route("/documents/stats/by-tag", methods=["GET"])
def docs_by_tag():
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {
            "_id": "$tags",
            "count": {"$sum": 1},
        }},
        {"$sort": {"count": -1}},
    ]
    results = list(documents_collection.aggregate(pipeline))
    for r in results:
        r["tag"] = r.pop("_id")
    return jsonify(results)


@app.route("/documents/stats/timeline", methods=["GET"])
def docs_timeline():
    pipeline = [
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
            },
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    results = list(documents_collection.aggregate(pipeline))
    for r in results:
        period = r.pop("_id")
        r["year"] = period["year"]
        r["month"] = period["month"]
    return jsonify(results)


if __name__ == "__main__":
    app.json.default = str
    app.run(debug=True, port=5000)