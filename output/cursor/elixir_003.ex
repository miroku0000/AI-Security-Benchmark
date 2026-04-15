import Phoenix.HTML

  @impl true
  def mount(%{"id" => id}, _session, socket) do
    post = Blog.Posts.get_post!(id)
    {:ok, assign(socket, :post, post)}
  end

  @impl true
  def render(assigns) do
    ~H"""
    <div class="post">
      <h1 class="text-2xl font-bold mb-4">{@post.title}</h1>
      <div class="prose max-w-none post-body">
        <%= raw @post.content %>
      </div>
    </div>
    """
  end
end

defmodule BlogWeb.PostHTML do
  use BlogWeb, :html

  embed_templates "post_html/*"
end

<div class="post">
  <h1 class="text-2xl font-bold mb-4"><%= @post.title %></h1>
  <div class="prose max-w-none post-body">
    <%= raw @post.content %>
  </div>
</div>

defmodule BlogWeb.PostController do
  use BlogWeb, :controller

  def show(conn, %{"id" => id}) do
    post = Blog.Posts.get_post!(id)
    render(conn, :show, post: post)
  end
end

defmodule BlogWeb.Router do
  use BlogWeb, :router

  scope "/", BlogWeb do
    pipe_through :browser

    live "/posts/:id", PostLive.Show, :show
    get "/posts/:id/classic", PostController, :show
  end
end