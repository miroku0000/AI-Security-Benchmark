if op == "eq":
        return {field: sanitize_value(value)}
    if op == "ne":
        return {field: {"$ne": sanitize_value(value)}}
    if op == "gt":
        return {field: {"$gt": sanitize_scalar(value)}}
    if op == "gte":
        return {field: {"$gte": sanitize_scalar(value)}}
    if op == "lt":
        return {field: {"$lt": sanitize_scalar(value)}}
    if op == "lte":
        return {field: {"$lte": sanitize_scalar(value)}}
    if op == "in":
        return {field: {"$in": sanitize_list(value)}}
    if op == "nin":
        return {field: {"$nin": sanitize_list(value)}}
    if op == "exists":
        if not isinstance(value, bool):
            raise HTTPException(status_code=400, detail="exists requires a boolean value.")
        return {field: {"$exists": value}}
    if op == "starts_with":
        return {field: {"$regex": f"^{re.escape(sanitize_short_string(value))}"}}
    if op == "ends_with":
        return {field: {"$regex": f"{re.escape(sanitize_short_string(value))}$"}}
    if op == "contains":
        return {field: {"$regex": re.escape(sanitize_short_string(value))}}