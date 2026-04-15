if operator in {"IN", "NOT IN"}:
            if not isinstance(value, list) or not value:
                raise ValueError(f"value for {operator} must be a non-empty list")
            placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in value)
            clauses.append(
                sql.SQL("{} {} ({})").format(
                    column_sql,
                    sql.SQL(operator),
                    placeholders,
                )
            )
            params.extend(value)
            continue