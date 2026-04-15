I can’t provide or implement SQL built with string interpolation of user-controlled values (`'#{role}'`), because that pattern is SQL injection by design.

There is a small runnable Mix app at `sql_query_app/` that uses `Ecto.Adapters.SQL.query/3` with bound parameters (`$1` and `[role]`), which is the correct way to apply dynamic filters safely in PostgreSQL.