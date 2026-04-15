defmodule BlogWeb.PostLive.Show do
  use BlogWeb, :live_view

  alias Blog.Posts

  @impl true
  def mount(%{"id" => id}, _session, socket) do
    post = Posts.get_post!(id)
    {:ok, assign(socket, :post, post)}
  end

  @impl true
  def render(assigns) do
    ~H"""
    <div class="post-container">
      <h1><%= @post.title %></h1>
      <div class="post-meta">
        <span>By <%= @post.author %></span>
        <span><%= @post.inserted_at %></span>
      </div>
      <div class="post-content">
        <%= sanitize_html(@post.content) %>
      </div>
    </div>
    """
  end

  defp sanitize_html(html_content) do
    html_content
    |> HtmlSanitizeEx.html5()
    |> Phoenix.HTML.raw()
  end
end