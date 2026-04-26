defmodule MyAppWeb.SessionManager do
  @moduledoc false

  import Plug.Conn

  @cookie_name "_my_app_session"
  @salt "session-cookie-v1"
  @max_age 7 * 24 * 60 * 60

  def fetch_session(conn, secret_key_base) when is_binary(secret_key_base) do
    conn = fetch_cookies(conn)

    session =
      conn.cookies[@cookie_name]
      |> verify(secret_key_base)
      |> decode_session()

    assign(conn, :session_state, session)
  end

  def put_session(conn, secret_key_base, session_state)
      when is_binary(secret_key_base) and is_map(session_state) do
    payload =
      session_state
      |> :erlang.term_to_binary()
      |> Base.url_encode64(padding: false)
      |> sign(secret_key_base)

    conn
    |> assign(:session_state, session_state)
    |> put_resp_cookie(@cookie_name, payload,
      http_only: true,
      secure: true,
      same_site: "Lax",
      max_age: @max_age
    )
  end

  def drop_session(conn) do
    conn
    |> assign(:session_state, %{})
    |> delete_resp_cookie(@cookie_name, http_only: true, secure: true, same_site: "Lax")
  end

  def session(conn) do
    conn.assigns[:session_state] || %{}
  end

  defp sign(encoded_binary, secret_key_base) do
    Plug.Crypto.MessageVerifier.sign(encoded_binary, secret_key_base, salt: @salt)
  end

  defp verify(nil, _secret_key_base), do: nil

  defp verify(cookie, secret_key_base) do
    Plug.Crypto.MessageVerifier.verify(cookie, secret_key_base, salt: @salt)
  end

  defp decode_session(nil), do: %{}

  defp decode_session(encoded_binary) do
    with {:ok, binary} <- Base.url_decode64(encoded_binary, padding: false),
         term <- :erlang.binary_to_term(binary, [:safe]),
         true <- is_map(term) do
      term
    else
      _ -> %{}
    end
  end
end

defmodule MyAppWeb.SessionPlug do
  @moduledoc false

  @behaviour Plug

  import Plug.Conn

  alias MyAppWeb.SessionManager

  def init(opts), do: opts

  def call(conn, opts) do
    secret_key_base =
      Keyword.get(opts, :secret_key_base) ||
        conn.secret_key_base ||
        raise ArgumentError, "missing :secret_key_base for SessionPlug"

    conn
    |> SessionManager.fetch_session(secret_key_base)
    |> register_before_send(fn conn ->
      case conn.assigns[:session_state] do
        nil -> conn
        session_state when is_map(session_state) -> SessionManager.put_session(conn, secret_key_base, session_state)
      end
    end)
  end

  def put_session(conn, key, value) do
    current =
      conn.assigns[:session_state]
      |> normalize_session()

    assign(conn, :session_state, Map.put(current, key, value))
  end

  def delete_session(conn, key) do
    current =
      conn.assigns[:session_state]
      |> normalize_session()

    assign(conn, :session_state, Map.delete(current, key))
  end

  def clear_session(conn) do
    assign(conn, :session_state, %{})
  end

  def get_session(conn, key, default \\ nil) do
    conn.assigns[:session_state]
    |> normalize_session()
    |> Map.get(key, default)
  end

  defp normalize_session(session) when is_map(session), do: session
  defp normalize_session(_), do: %{}
end

defmodule MyAppWeb.ExampleController do
  use Phoenix.Controller, formats: [:json]

  alias MyAppWeb.SessionPlug

  def show(conn, _params) do
    json(conn, %{session: conn.assigns[:session_state] || %{}})
  end

  def put_value(conn, %{"key" => key, "value" => value}) do
    conn
    |> SessionPlug.put_session(key, value)
    |> json(%{session: conn.assigns[:session_state]})
  end

  def delete_value(conn, %{"key" => key}) do
    conn
    |> SessionPlug.delete_session(key)
    |> json(%{session: conn.assigns[:session_state]})
  end

  def clear(conn, _params) do
    conn
    |> SessionPlug.clear_session()
    |> json(%{session: %{}})
  end
end

defmodule MyAppWeb.Router do
  use Phoenix.Router

  pipeline :browser_with_custom_session do
    plug :accepts, ["html", "json"]
    plug MyAppWeb.SessionPlug
  end

  scope "/", MyAppWeb do
    pipe_through :browser_with_custom_session

    get "/session", ExampleController, :show
    post "/session", ExampleController, :put_value
    delete "/session/:key", ExampleController, :delete_value
    delete "/session", ExampleController, :clear
  end
end