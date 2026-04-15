@app.route("/reports/documents/by-author", methods=["GET"])
def report_documents_by_author():
    pipeline = [
        {
            "$group": {
                "_id": "$author_id",
                "document_count": {"$sum": 1},
                "last_updated": {"$max": "$updated_at"},
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "author",
            }
        },
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "author_id": "$_id",
                "document_count": 1,
                "last_updated": 1,
                "author": {
                    "_id": "$author._id",
                    "username": "$author.username",
                    "email": "$author.email",
                    "full_name": "$author.full_name",
                },
            }
        },
        {"$sort": {"document_count": -1}},
    ]
    result = list(documents_collection.aggregate(pipeline))
    return json_response({"items": [serialize_document(item) for item in result]})