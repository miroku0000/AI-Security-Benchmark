import Config

config :devops_automation, DevopsAutomationWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  render_errors: [formats: [json: DevopsAutomationWeb.ErrorJSON], layout: false],
  pubsub_server: DevopsAutomation.PubSub

config :phoenix, :json_library, Jason

import_config "#{config_env()}.exs"
