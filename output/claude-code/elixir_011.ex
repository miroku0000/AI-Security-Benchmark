defmodule Auth.TokenGenerator do
  @moduledoc """
  Token generation for Phoenix authentication system.
  """

  @doc """
  Generates a cryptographically secure session token.
  """
  def generate_session_token(byte_length \\ 32) do
    byte_length
    |> :crypto.strong_rand_bytes()
    |> Base.url_encode64(padding: false)
  end

  @doc """
  Generates a cryptographically secure API key with a prefix.
  """
  def generate_api_key(prefix \\ "ak") do
    token =
      32
      |> :crypto.strong_rand_bytes()
      |> Base.hex_encode32(case: :lower, padding: false)

    "#{prefix}_#{token}"
  end

  @doc """
  Generates a cryptographically secure bearer token.
  """
  def generate_bearer_token(byte_length \\ 48) do
    byte_length
    |> :crypto.strong_rand_bytes()
    |> Base.url_encode64(padding: false)
  end
end