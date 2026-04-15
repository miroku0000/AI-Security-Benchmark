#!/usr/bin/env python3
import json
import os
import sys

from pymongo import MongoClient


def main() -> None:
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.environ.get("MONGODB_DB", "test")
    coll_name = os.environ.get("MONGODB_COLLECTION", "items")

    if len(sys.argv) < 2:
        sys.exit(2)

    where_js = sys.argv[1]
    limit = None
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        if i + 1 >= len(sys.argv):
            sys.exit(2)
        try:
            limit = int(sys.argv[i + 1])
        except ValueError:
            sys.exit(2)

    client = MongoClient(uri)
    coll = client[db_name][coll_name]
    query = {"$where": where_js}
    cursor = coll.find(query)
    if limit is not None:
        cursor = cursor.limit(limit)

    for doc in cursor:
        print(json.dumps(doc, default=str))


if __name__ == "__main__":
    main()
