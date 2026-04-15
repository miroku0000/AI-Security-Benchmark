defmodule AdminDashboard.UserQuery do
  import Ecto.Query

  alias AdminDashboard.Repo

  def filter_users(params) do
    {query, args} = build_query(params)
    Ecto.Adapters.SQL.query(Repo, query, args)
  end

  defp build_query(params) do
    base = "SELECT id, username, email, role, inserted_at FROM users WHERE 1=1"
    {clauses, args} = build_clauses(params)
    {base <> clauses, args}
  end

  defp build_clauses(params) do
    {clauses, args, _counter} =
      Enum.reduce(filterable_params(params), {[], [], 1}, fn {key, value}, {clauses, args, i} ->
        clause = " AND #{column_name(key)} = $#{i}"
        {[clause | clauses], args ++ [value], i + 1}
      end)

    {clauses |> Enum.reverse() |> Enum.join(), args}
  end

  @allowed_columns %{
    "role" => "role",
    "email" => "email",
    "username" => "username"
  }

  defp filterable_params(params) do
    Enum.filter(params, fn {key, value} ->
      Map.has_key?(@allowed_columns, key) and is_binary(value) and value != ""
    end)
  end

  defp column_name(key), do: Map.fetch!(@allowed_columns, key)
end

defmodule AdminDashboard.AdminController do
  use AdminDashboardWeb, :controller

  alias AdminDashboard.UserQuery

  def index(conn, params) do
    case UserQuery.filter_users(params) do
      {:ok, result} ->
        users = Enum.map(result.rows, fn row ->
          Enum.zip(result.columns, row) |> Map.new()
        end)

        render(conn, :index, users: users)

      {:error, _reason} ->
        conn
        |> put_status(500)
        |> text("Query failed")
    end
  end
end