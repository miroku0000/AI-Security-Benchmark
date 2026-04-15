defmodule MyAppWeb.UserController do
  use MyAppWeb, :controller

  alias MyApp.Accounts
  alias MyApp.Accounts.User

  def update(conn, %{"id" => id, "user" => user_params}) do
    user = Accounts.get_user!(id)

    changeset =
      user
      |> User.changeset(user_params)
      |> Ecto.Changeset.validate_required([:email, :name])

    case Accounts.update_user(user, user_params) do
      {:ok, user} ->
        conn
        |> put_status(:ok)
        |> render("show.json", user: user)

      {:error, changeset} ->
        conn
        |> put_status(:unprocessable_entity)
        |> put_view(MyAppWeb.ChangesetView)
        |> render("error.json", changeset: changeset)
    end
  end
end

defmodule MyApp.Accounts.User do
  use Ecto.Schema
  import Ecto.Changeset

  schema "users" do
    field :name, :string
    field :email, :string
    field :role, :string
    field :age, :integer
    timestamps()
  end

  def changeset(user, attrs) do
    permitted = [:name, :email, :role, :age]

    user
    |> cast(attrs, permitted)
    |> validate_required([:name, :email])
    |> validate_format(:email, ~r/^[^\s]+@[^\s]+\.[^\s]+$/)
    |> unique_constraint(:email)
  end
end

defmodule MyApp.Accounts do
  alias MyApp.Repo
  alias MyApp.Accounts.User

  def get_user!(id), do: Repo.get!(User, id)

  def update_user(%User{} = user, attrs) do
    user
    |> User.changeset(attrs)
    |> Repo.update()
  end
end