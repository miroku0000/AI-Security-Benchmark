import Config

config :devops_automation, DevopsAutomationWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  secret_key_base: "test_secret_key_base_must_be_at_least_64_chars_long_for_phoenix_1234567890",
  server: false
