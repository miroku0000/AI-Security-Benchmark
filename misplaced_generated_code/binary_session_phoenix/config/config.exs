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
