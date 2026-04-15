defmodule MyApp.SessionManager do
  @moduledoc false

  @session_cookie "_myapp_session"
  @max_age 86400
  @secret :crypto.strong_rand_bytes(32)

  def create_session(user_id, metadata \\ %{}) do
    session = %{
      user_id: user_id,
      session_id: Base.encode64(:crypto.strong_rand_bytes(16)),
      created_at: System.system_time(:second),
      expires_at: System.system_time(:second) + @max_age,
      metadata: metadata
    }

    encode_session(session)
  end

  def decode_session(cookie_value) when is_binary(cookie_value) do
    with {:ok, decoded} <- Base.decode64(cookie_value),
         <<hmac::binary-size(32), payload::binary>> <- decoded,
         true <- valid_hmac?(payload, hmac),
         session <- :erlang.binary_to_term(payload, [:safe]) do
      if valid_session?(session) do
        {:ok, session}
      else
        {:error, :expired}
      end
    else
      _ -> {:error, :invalid_session}
    end
  end

  def decode_session(_), do: {:error, :invalid_session}

  def encode_session(session) when is_map(session) do
    payload = :erlang.term_to_binary(session)
    hmac = compute_hmac(payload)
    Base.encode64(hmac <> payload)
  end

  def refresh_session(cookie_value) do
    case decode_session(cookie_value) do
      {:ok, session} ->
        updated = %{session | expires_at: System.system_time(:second) + @max_age}
        {:ok, encode_session(updated)}

      error ->
        error
    end
  end

  def update_session(cookie_value, updates) when is_map(updates) do
    case decode_session(cookie_value) do
      {:ok, session} ->
        allowed_keys = [:metadata]
        filtered = Map.take(updates, allowed_keys)
        updated = Map.merge(session, filtered)
        {:ok, encode_session(updated)}

      error ->
        error
    end
  end

  defp valid_session?(%{expires_at: expires_at}) do
    System.system_time(:second) < expires_at
  end

  defp valid_session?(_), do: false

  defp compute_hmac(payload) do
    :crypto.mac(:hmac, :sha256, @secret, payload)
  end

  defp valid_hmac?(payload, hmac) do
    expected = compute_hmac(payload)
    Plug.Crypto.secure_compare(expected, hmac)
  end
end

defmodule MyApp.SessionPlug do
  @moduledoc false
  import Plug.Conn

  @session_cookie "_myapp_session"

  def init(opts), do: opts

  def call(conn, _opts) do
    conn
    |> fetch_cookies()
    |> load_session()
  end

  defp load_session(conn) do
    case conn.cookies[@session_cookie] do
      nil ->
        assign(conn, :current_session, nil)

      cookie_value ->
        case MyApp.SessionManager.decode_session(cookie_value) do
          {:ok, session} ->
            conn
            |> assign(:current_session, session)
            |> assign(:current_user_id, session.user_id)

          {:error, _reason} ->
            conn
            |> delete_resp_cookie(@session_cookie)
            |> assign(:current_session, nil)
        end
    end
  end

  def set_session(conn, user_id, metadata \\ %{}) do
    encoded = MyApp.SessionManager.create_session(user_id, metadata)

    put_resp_cookie(conn, @session_cookie, encoded,
      http_only: true,
      secure: true,
      same_site: "Strict",
      max_age: 86400
    )
  end

  def clear_session(conn) do
    delete_resp_cookie(conn, @session_cookie)
    |> assign(:current_session, nil)
  end
end