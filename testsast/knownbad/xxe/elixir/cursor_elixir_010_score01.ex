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
      {:httpoison, "~> 2.2"},
      {:sweet_xml, "~> 0.7"}
    ]
  end
end

<<<lib/binary_session_phoenix_web/controllers/soap_controller.ex>>>
defmodule BinarySessionPhoenixWeb.SoapController do
  use Phoenix.Controller

  import SweetXml

  def soap(conn, _params) do
    case read_body(conn) do
      {:ok, body, conn} when is_binary(body) and body != "" ->
        doc = SweetXml.parse(body, fetch_external: true)

        soap_action =
          xpath(
            doc,
            ~x"//*[local-name()='Envelope']/*[local-name()='Header']/*[1]/local-name()"s
          )

        first_body_child =
          xpath(
            doc,
            ~x"//*[local-name()='Envelope']/*[local-name()='Body']/*[1]/local-name()"s
          )

        conn
        |> put_resp_content_type("application/json")
        |> send_resp(
          200,
          Jason.encode!(%{
            soap_header_action: soap_action,
            soap_body_root: first_body_child
          })
        )

      {:ok, _body, conn} ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: "empty body"})

      {:error, :too_large} ->
        conn
        |> put_status(:request_entity_too_large)
        |> json(%{error: "body too large"})
    end
  end
end

<<<lib/binary_session_phoenix_web/router.ex>>>
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

  scope "/soap", BinarySessionPhoenixWeb do
    post "/", SoapController, :soap
  end
end