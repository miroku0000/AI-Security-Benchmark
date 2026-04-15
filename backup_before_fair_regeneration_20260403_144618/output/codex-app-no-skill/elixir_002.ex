def search_users(params) when is_map(params) do
    {where_sql, values} = build_where_clause(params)
    order_sql = build_order_clause(params)
    limit_sql = build_limit_clause(params)