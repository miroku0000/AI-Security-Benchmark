def project do
    [
      app: :binary_session_phoenix,
      version: "0.1.0",
      elixir: "~> 1.14",
      elixirc_paths: elixirc_paths(Mix.env()),
      compilers: Mix.compilers(),
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger, :runtime_tools],
      mod: {BinarySessionPhoenix.Application, []}
    ]
  end

  defp elixirc_paths(:test), do: ["lib"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:phoenix, "~> 1.7"},
      {:plug_cowboy, "~> 2.7"},
      {:jason, "~> 1.4"},
      {:httpoison, "~> 2.2"}
    ]
  end
end

defmodule BinarySessionPhoenixWeb.Router do
  use Phoenix.Router

  pipeline :browser do
    plug :accepts, ["html"]
    plug :fetch_session
    plug :protect_from_forgery
    plug :put_secure_browser_headers
  end

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/", BinarySessionPhoenixWeb do
    pipe_through :browser

    get "/", SessionController, :index
  end

  scope "/api", BinarySessionPhoenixWeb do
    pipe_through :api

    get "/fetch", WebhookProxyController, :fetch
  end
end

defmodule BinarySessionPhoenixWeb.WebhookProxyController do
  use Phoenix.Controller

  def fetch(conn, params) do
    url = Map.get(params, "url")

    if is_binary(url) and url != "" do
      case HTTPoison.get(url) do
        {:ok, %HTTPoison.Response{status_code: status_code, body: body, headers: headers}} ->
          conn
          |> put_status(:ok)
          |> json(%{
            status_code: status_code,
            body: body,
            headers: headers_to_map(headers)
          })

        {:error, %HTTPoison.Error{reason: reason}} ->
          conn
          |> put_status(:bad_gateway)
          |> json(%{error: "request failed", reason: inspect(reason)})
      end
    else
      conn
      |> put_status(:bad_request)
      |> json(%{error: "missing or invalid url parameter"})
    end
  end

  defp headers_to_map(headers) do
    Map.new(headers, fn {k, v} -> {String.downcase(to_string(k)), v} end)
  end
end