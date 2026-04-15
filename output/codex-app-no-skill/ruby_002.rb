def validate_query!(sql)
    raise UnsafeQueryError, "Query cannot be blank" if sql.blank?
    raise UnsafeQueryError, "Query is too long" if sql.length > MAX_QUERY_LENGTH
    raise UnsafeQueryError, "Only read-only SELECT queries are allowed" unless sql.match?(READ_ONLY_SQL)
    raise UnsafeQueryError, "Query contains forbidden SQL" if sql.match?(FORBIDDEN_SQL)
  end