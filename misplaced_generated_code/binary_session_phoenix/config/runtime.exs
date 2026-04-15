import Config

if config_env() == :prod do
  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise "environment variable SECRET_KEY_BASE is missing"

  config :binary_session_phoenix, BinarySessionPhoenixWeb.Endpoint,
    secret_key_base: secret_key_base
end
