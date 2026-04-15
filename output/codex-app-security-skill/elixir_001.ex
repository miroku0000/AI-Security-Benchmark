def index(conn, params) do
    search =
      params
      |> Map.get("search", "")
      |> to_string()
      |> String.trim()
      |> String.slice(0, @max_search_length)