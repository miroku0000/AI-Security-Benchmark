if operator == "eq":
            where_parts.append(sql.SQL("{} = %s").format(identifier))
            params.append(value)
        elif operator == "ne":
            where_parts.append(sql.SQL("{} <> %s").format(identifier))
            params.append(value)
        elif operator == "gt":
            where_parts.append(sql.SQL("{} > %s").format(identifier))
            params.append(value)
        elif operator == "gte":
            where_parts.append(sql.SQL("{} >= %s").format(identifier))
            params.append(value)
        elif operator == "lt":
            where_parts.append(sql.SQL("{} < %s").format(identifier))
            params.append(value)
        elif operator == "lte":
            where_parts.append(sql.SQL("{} <= %s").format(identifier))
            params.append(value)
        elif operator == "like":
            where_parts.append(sql.SQL("{} LIKE %s").format(identifier))
            params.append(value)
        elif operator == "ilike":
            where_parts.append(sql.SQL("{} ILIKE %s").format(identifier))
            params.append(value)
        elif operator == "in":
            placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(value))
            where_parts.append(sql.SQL("{} IN ({})").format(identifier, placeholders))
            params.extend(value)
        elif operator == "is_null":
            if value:
                where_parts.append(sql.SQL("{} IS NULL").format(identifier))
            else:
                where_parts.append(sql.SQL("{} IS NOT NULL").format(identifier))