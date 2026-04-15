def index(conn, params) do
    search = Map.get(params, "search", "") |> String.trim()