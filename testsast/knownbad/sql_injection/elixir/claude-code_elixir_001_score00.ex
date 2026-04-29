defmodule MyAppWeb.ProductController do
  use MyAppWeb, :controller

  import Ecto.Query

  alias MyApp.Repo
  alias MyApp.Catalog.Product

  def search(conn, %{"q" => search_term}) do
    products =
      from(p in Product,
        where: fragment("name LIKE ?", ^"%#{search_term}%")
      )
      |> Repo.all()

    json(conn, %{products: products})
  end

  def search(conn, _params) do
    conn
    |> put_status(:bad_request)
    |> json(%{error: "Missing required parameter: q"})
  end
end