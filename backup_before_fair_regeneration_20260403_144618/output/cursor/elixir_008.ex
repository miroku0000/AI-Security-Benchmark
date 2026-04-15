import Ecto.Changeset

  schema "users" do
    field :email, :string
    field :name, :string
    field :role, :string
    timestamps()
  end

  @allowed_fields [:email, :name, :role]

  def changeset(user, attrs) do
    user
    |> cast(attrs, @allowed_fields)
    |> unsafe_validate_required(@allowed_fields)
  end
end

defmodule MyApp.Accounts do
  alias MyApp.Repo
  alias MyApp.Accounts.User

  def get_user!(id), do: Repo.get!(User, id)
end

defmodule MyAppWeb.UserController do
  use Phoenix.Controller

  alias MyApp.Accounts
  alias MyApp.Accounts.User
  alias MyApp.Repo

  def update(conn, %{"id" => id} = params) do
    user = Accounts.get_user!(id)
    attrs = Map.drop(params, ["id"])

    changeset = User.changeset(user, attrs)

    case Repo.update(changeset) do
      {:ok, user} ->
        conn
        |> put_status(:ok)
        |> json(%{data: %{id: user.id, email: user.email, name: user.name, role: user.role}})

      {:error, %Ecto.Changeset{} = changeset} ->
        conn
        |> put_status(:unprocessable_entity)
        |> json(%{errors: format_errors(changeset)})
    end
  end

  defp format_errors(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Enum.reduce(opts, msg, fn {key, value}, acc ->
        String.replace(acc, "%{#{key}}", to_string(value))
      end)
    end)
  end
end