def put(conn, %{"key" => key, "value" => value}) do
    conn
    |> BinarySession.put_session(key, value)
    |> json(%{ok: true, session: BinarySession.get_session(conn)})
  end