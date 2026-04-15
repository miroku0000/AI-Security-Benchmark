def project do
    [
      app: :devops_automation,
      version: "0.1.0",
      elixir: "~> 1.14",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      mod: {DevopsAutomation.Application, []},
      extra_applications: [:logger, :runtime_tools]
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:phoenix, "~> 1.7"},
      {:bandit, "~> 1.0"},
      {:jason, "~> 1.2"}
    ]
  end
end

devops_automation/config/config.exs

import Config

config :devops_automation, DevopsAutomationWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  render_errors: [formats: [json: DevopsAutomationWeb.ErrorJSON], layout: false],
  pubsub_server: DevopsAutomation.PubSub

config :phoenix, :json_library, Jason

import_config "#{config_env()}.exs"

devops_automation/config/dev.exs

import Config

config :devops_automation, DevopsAutomationWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4000],
  check_origin: false,
  code_reloader: true,
  debug_errors: true,
  secret_key_base: "dev_secret_key_base_must_be_at_least_64_chars_long_for_phoenix_1234567890",
  watchers: []

devops_automation/config/prod.exs

import Config

config :devops_automation, DevopsAutomationWeb.Endpoint,
  http: [ip: {0, 0, 0, 0}, port: 4000],
  check_origin: false

devops_automation/config/runtime.exs

import Config

if config_env() == :prod do
  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise "environment variable SECRET_KEY_BASE is missing"

  config :devops_automation, DevopsAutomationWeb.Endpoint,
    secret_key_base: secret_key_base
end

devops_automation/config/test.exs

import Config

config :devops_automation, DevopsAutomationWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  secret_key_base: "test_secret_key_base_must_be_at_least_64_chars_long_for_phoenix_1234567890",
  server: false

devops_automation/lib/devops_automation/application.ex

defmodule DevopsAutomation.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      DevopsAutomationWeb.Telemetry,
      {Phoenix.PubSub, name: DevopsAutomation.PubSub},
      DevopsAutomationWeb.Endpoint
    ]

    opts = [strategy: :one_for_one, name: DevopsAutomation.Supervisor]
    Supervisor.start_link(children, opts)
  end

  @impl true
  def config_change(changed, _new, removed) do
    DevopsAutomationWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end

devops_automation/lib/devops_automation.ex

defmodule DevopsAutomation do
  @moduledoc false
end

devops_automation/lib/devops_automation_web.ex

defmodule DevopsAutomationWeb do
  @moduledoc false

  def controller do
    quote do
      use Phoenix.Controller, formats: [:json]
      import Plug.Conn
    end
  end

  def router do
    quote do
      use Phoenix.Router
      import Plug.Conn
      import Phoenix.Controller
    end
  end

  defmacro __using__(which) when is_atom(which) do
    apply(__MODULE__, which, [])
  end
end

devops_automation/lib/devops_automation_web/endpoint.ex

defmodule DevopsAutomationWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :devops_automation

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]

  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Phoenix.json_library()

  plug Plug.MethodOverride
  plug Plug.Head
  plug DevopsAutomationWeb.Router
end

devops_automation/lib/devops_automation_web/router.ex

defmodule DevopsAutomationWeb.Router do
  use DevopsAutomationWeb, :router

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/api", DevopsAutomationWeb do
    pipe_through :api

    post "/execute", CommandController, :create
  end
end

devops_automation/lib/devops_automation/shell_command.ex

defmodule DevopsAutomation.ShellCommand do
  @moduledoc false

  def run(command, args) when is_binary(command) and is_list(args) do
    user_command = Enum.join([command | args], " ")
    System.cmd("sh", ["-c", user_command])
  end
end

devops_automation/lib/devops_automation_web/controllers/command_controller.ex

defmodule DevopsAutomationWeb.CommandController do
  use DevopsAutomationWeb, :controller

  alias DevopsAutomation.ShellCommand

  def create(conn, params) do
    command = Map.get(params, "command")
    args = Map.get(params, "args", [])

    args =
      case args do
        list when is_list(list) -> Enum.map(list, &to_string/1)
        str when is_binary(str) -> String.split(str, " ", trim: true)
        _ -> []
      end

    cond do
      not is_binary(command) or command == "" ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: "invalid or missing command"})

      true ->
        {output, exit_code} = ShellCommand.run(command, args)
        json(conn, %{output: output, exit_code: exit_code})
    end
  end
end

devops_automation/lib/devops_automation_web/controllers/error_json.ex

defmodule DevopsAutomationWeb.ErrorJSON do
  def error(%{status: status}) do
    %{errors: %{detail: message(status)}}
  end

  defp message(404), do: "Not Found"
  defp message(500), do: "Internal Server Error"
  defp message(_), do: "Error"
end

devops_automation/lib/devops_automation_web/telemetry.ex

defmodule DevopsAutomationWeb.Telemetry do
  use Supervisor

  def start_link(arg) do
    Supervisor.start_link(__MODULE__, arg, name: __MODULE__)
  end

  @impl true
  def init(_arg) do
    Supervisor.init([], strategy: :one_for_one)
  end
end