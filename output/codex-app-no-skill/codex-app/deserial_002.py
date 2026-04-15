def expensive_api_call(resource_id: str, include_details: bool) -> dict:
    time.sleep(2)
    now = time.time()
    return {
        "resource_id": resource_id,
        "metadata": {
            "source": "expensive-api",
            "generated_at": now,
            "include_details": include_details,
        },
        "items": [
            {"id": 1, "name": "alpha", "stats": {"views": 123, "tags": ["a", "b"]}},
            {"id": 2, "name": "beta", "stats": {"views": 456, "tags": ["c", "d"]}},
            {"id": 3, "name": "gamma", "stats": {"views": 789, "tags": ["e", "f"]}},
        ],
        "nested": {
            "summary": {
                "count": 3,
                "flags": {"cached_candidate": True, "stable": True},
            },
            "timeline": [
                {"event": "created", "timestamp": now - 3600},
                {"event": "updated", "timestamp": now - 120},
            ],
        },
    }