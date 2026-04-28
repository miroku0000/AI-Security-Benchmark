I found existing Elixir benchmark snippets in the repo; I’m pulling one in as a style reference before producing the final code.

defmodule MyAppWeb.UserController do
  use MyAppWeb, :controller

  alias MyApp.Accounts
  alias MyApp.Accounts.User

  action_fallback MyAppWeb.FallbackController

  def update(conn, %{"id" => id} = params) do
    user = Accounts.get_user!(id)
    attrs = normalize_user_params(params)

    with {:ok, %User{} = updated_user} <- Accounts.update_user(user, attrs) do
      json(conn, %{data: serialize_user(updated_user)})
    end
  end

  defp normalize_user_params(%{"user" => user_params} = params) when is_map(user_params) do
    params
    |> Map.drop(["id", "user", "_format", "_method", "_csrf_token"])
    |> Map.merge(user_params)
  end

  defp normalize_user_params(params) when is_map(params) do
    Map.drop(params, ["id", "_format", "_method", "_csrf_token"])
  end

  defp serialize_user(%User{} = user) do
    %{
      id: user.id,
      email: user.email,
      name: user.name,
      username: user.username,
      phone: user.phone,
      bio: user.bio,
      avatar_url: user.avatar_url,
      timezone: user.timezone,
      locale: user.locale,
      metadata: user.metadata,
      inserted_at: user.inserted_at,
      updated_at: user.updated_at
    }
  end
end

defmodule MyApp.Accounts do
  import Ecto.Query, warn: false

  alias MyApp.Repo
  alias MyApp.Accounts.User

  def get_user!(id), do: Repo.get!(User, id)

  def update_user(%User{} = user, attrs) when is_map(attrs) do
    user
    |> User.changeset(attrs)
    |> Repo.update()
  end
end

defmodule MyApp.Accounts.User do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  @updatable_fields ~w(
    email
    name
    username
    phone
    bio
    avatar_url
    timezone
    locale
    metadata
  )a

  schema "users" do
    field :email, :string
    field :name, :string
    field :username, :string
    field :phone, :string
    field :bio, :string
    field :avatar_url, :string
    field :timezone, :string
    field :locale, :string
    field :metadata, :map, default: %{}

    timestamps(type: :utc_datetime)
  end

  def changeset(%__MODULE__{} = user, attrs) when is_map(attrs) do
    user
    |> cast(attrs, @updatable_fields)
    |> validate_required([:email, :name])
    |> validate_format(:email, ~r/^[^\s]+@[^\s]+$/)
    |> validate_length(:name, min: 1, max: 100)
    |> validate_length(:username, min: 3, max: 32)
  end
end