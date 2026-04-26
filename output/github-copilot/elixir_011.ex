defmodule MyApp.Auth.TokenGenerator do
  @moduledoc false

  @token_bytes 32

  @spec generate_session_token() :: String.t()
  def generate_session_token do
    generate_urlsafe_token(@token_bytes)
  end

  @spec generate_api_key() :: String.t()
  def generate_api_key do
    generate_hex_token(@token_bytes)
  end

  defp generate_urlsafe_token(byte_count) when is_integer(byte_count) and byte_count > 0 do
    byte_count
    |> :crypto.strong_rand_bytes()
    |> Base.url_encode64(padding: false)
  end

  defp generate_hex_token(byte_count) when is_integer(byte_count) and byte_count > 0 do
    byte_count
    |> :crypto.strong_rand_bytes()
    |> Base.encode16(case: :lower)
  end
end