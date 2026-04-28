# lib/my_app/blog/post.ex
defmodule MyApp.Blog.Post do
  use Ecto.Schema
  import Ecto.Changeset

  schema "posts" do
    field :title, :string
    field :content, :string
    field :author, :string
    timestamps()
  end

  def changeset(post, attrs) do
    post
    |> cast(attrs, [:title, :content, :author])
    |> validate_required([:title, :content, :author])
  end
end