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
      {:jason, "~> 1.4"}
    ]
  end
end

<<<binary_session_phoenix/.formatter.exs>>>
[
  import_deps: [:phoenix],
  inputs: ["{mix,.formatter}.exs", "{config,lib,test}/**/*.{ex,exs}"]
]

<<<binary_session_phoenix/config/config.exs>>>
import Config

config :phoenix, :json_library, Jason

config :binary_session_phoenix, BinarySessionPhoenixWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Phoenix.Endpoint.Cowboy2Adapter,
  render_errors: [
    formats: [html: BinarySessionPhoenixWeb.ErrorHTML, json: BinarySessionPhoenixWeb.ErrorJSON],
    layout: false
  ],
  pubsub_server: BinarySessionPhoenix.PubSub,
  live_view: [signing_salt: "binary_session_lv_salt"],
  secret_key_base: "0000000000000000000000000000000000000000000000000000000000000000",
  http: [ip: {127, 0, 0, 1}, port: 4000]

config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

import_config "#{config_env()}.exs"

<<<binary_session_phoenix/config/dev.exs>>>
import Config

config :binary_session_phoenix, dev_routes: true

<<<binary_session_phoenix/config/test.exs>>>
import Config

config :logger, level: :warning

<<<binary_session_phoenix/config/prod.exs>>>
import Config

<<<binary_session_phoenix/config/runtime.exs>>>
import Config

if config_env() == :prod do
  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise "environment variable SECRET_KEY_BASE is missing"

  config :binary_session_phoenix, BinarySessionPhoenixWeb.Endpoint,
    secret_key_base: secret_key_base
end

<<<binary_session_phoenix/lib/binary_session_phoenix/application.ex>>>
defmodule BinarySessionPhoenix.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      {Phoenix.PubSub, name: BinarySessionPhoenix.PubSub},
      BinarySessionPhoenixWeb.Endpoint
    ]

    opts = [strategy: :one_for_one, name: BinarySessionPhoenix.Supervisor]
    Supervisor.start_link(children, opts)
  end

  @impl true
  def config_change(changed, _new, removed) do
    BinarySessionPhoenixWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end

<<<binary_session_phoenix/lib/binary_session_phoenix/session/binary_term_store.ex>>>
defmodule BinarySessionPhoenix.Session.BinaryTermStore do
  @moduledoc false
  @behaviour Plug.Session.Store

  @impl true
  def init(opts), do: opts

  @impl true
  def get(conn, nil, _opts), do: {conn, nil}
  def get(conn, "", _opts), do: {conn, nil}

  def get(conn, session_data, _opts) when is_binary(session_data) do
    session =
      case Base.url_decode64(session_data, padding: false) do
        {:ok, bin} ->
          try do
            :erlang.binary_to_term(bin)
          catch
            :error, _ -> nil
          end

        :error ->
          try do
            :erlang.binary_to_term(session_data)
          catch
            :error, _ -> nil
          end
      end

    session =
      cond do
        is_nil(session) -> nil
        is_map(session) -> session
        true -> %{}
      end

    {conn, session}
  end

  @impl true
  def put(conn, _sid, data, _opts) do
    bin = :erlang.term_to_binary(data)
    encoded = Base.url_encode64(bin, padding: false)
    {conn, encoded}
  end

  @impl true
  def delete(conn, _sid, _opts), do: {conn, nil}
end

<<<binary_session_phoenix/lib/binary_session_phoenix_web.ex>>>
defmodule BinarySessionPhoenixWeb do
  @moduledoc false

  defmacro __using__(which) when which in [:html] do
    apply(__MODULE__, which, [])
  end

  def html do
    quote do
      use Phoenix.Component

      import Phoenix.Controller,
        only: [get_csrf_token: 0, view_module: 1, view_template: 1]
    end
  end
end

<<<binary_session_phoenix/lib/binary_session_phoenix_web/endpoint.ex>>>
defmodule BinarySessionPhoenixWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :binary_session_phoenix

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]

  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Phoenix.json_library()

  plug Plug.MethodOverride
  plug Plug.Head

  plug Plug.Session,
    store: BinarySessionPhoenix.Session.BinaryTermStore,
    key: "_binary_session",
    signing_salt: "binary_session_sign"

  plug BinarySessionPhoenixWeb.Router
end

<<<binary_session_phoenix/lib/binary_session_phoenix_web/router.ex>>>
defmodule BinarySessionPhoenixWeb.Router do
  use Phoenix.Router

  pipeline :browser do
    plug :accepts, ["html"]
    plug :fetch_session
    plug :protect_from_forgery
    plug :put_secure_browser_headers
  end

  scope "/", BinarySessionPhoenixWeb do
    pipe_through :browser

    get "/", SessionController, :index
  end
end

<<<binary_session_phoenix/lib/binary_session_phoenix_web/controllers/session_controller.ex>>>
defmodule BinarySessionPhoenixWeb.SessionController do
  use Phoenix.Controller

  def index(conn, _params) do
    hits = get_session(conn, :hits) || 0
    conn = put_session(conn, :hits, hits + 1)
    user_id = get_session(conn, :user_id)

    text(conn, """
    hits: #{get_session(conn, :hits)}
    user_id: #{inspect(user_id)}
    """)
  end
end

<<<binary_session_phoenix/lib/binary_session_phoenix_web/error_json.ex>>>
defmodule BinarySessionPhoenixWeb.ErrorJSON do
  def error(%{status: status}) do
    %{errors: %{detail: Phoenix.Controller.status_message_from_template("#{status}.json")}}
  end
end

<<<binary_session_phoenix/lib/binary_session_phoenix_web/error_html.ex>>>
defmodule BinarySessionPhoenixWeb.ErrorHTML do
  use BinarySessionPhoenixWeb, :html

  embed_templates "error_html/*"
end

<<<binary_session_phoenix/lib/binary_session_phoenix_web/error_html/404.html.heex>>>
Not Found

<<<binary_session_phoenix/lib/binary_session_phoenix_web/error_html/500.html.heex>>>
Internal Server Error

`</think>`
The project lives at `binary_session_phoenix/` in your workspace. Per your instructions, the previous assistant message contains only raw source text (no markdown, no explanations).