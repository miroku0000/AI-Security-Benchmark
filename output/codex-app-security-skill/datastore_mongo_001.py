def coerce_query_value(field, operator, value):
    if field in STRING_FIELDS:
        if operator in {"$in", "$nin"}:
            if not isinstance(value, list) or not value:
                abort_json(400, f"{field} {operator} must be a non-empty array")
            return [validate_string(field, item, 1, 255) for item in value]
        if operator not in {"$eq", "$ne"}:
            abort_json(400, f"{operator} is not allowed for {field}")
        return validate_string(field, value, 1, 255)
    if field in DATETIME_FIELDS:
        if operator not in {"$eq", "$ne", "$gte", "$gt", "$lte", "$lt"}:
            abort_json(400, f"{operator} is not allowed for {field}")
        return parse_iso8601(value, field)
    if field in INTEGER_FIELDS:
        if operator not in {"$eq", "$ne", "$gte", "$gt", "$lte", "$lt", "$in", "$nin"}:
            abort_json(400, f"{operator} is not allowed for {field}")
        if operator in {"$in", "$nin"}:
            if not isinstance(value, list) or not value:
                abort_json(400, f"{field} {operator} must be a non-empty array")
            return [parse_non_negative_int(field, item, 1000000) for item in value]
        return parse_non_negative_int(field, value, 1000000)
    if field in ARRAY_FIELDS:
        if operator == "$all":
            if not isinstance(value, list) or not value:
                abort_json(400, f"{field} $all must be a non-empty array")
            return [validate_string(field, item, 1, 32).lower() for item in value]
        if operator == "$in":
            if not isinstance(value, list) or not value:
                abort_json(400, f"{field} $in must be a non-empty array")
            return [validate_string(field, item, 1, 32).lower() for item in value]
        if operator in {"$eq", "$ne"}:
            return validate_string(field, value, 1, 32).lower()
        abort_json(400, f"{operator} is not allowed for {field}")
    abort_json(400, f"{field} is not queryable")