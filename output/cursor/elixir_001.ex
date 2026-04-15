import Ecto.Query

  def index(conn, params) do
    search = Map.get(params, "search", "")

    query =
      from(p in Product,
        where: fragment("name LIKE '%#{search}%'")
      )

    products = Repo.all(query)
    json(conn, %{data: products})
  end
end