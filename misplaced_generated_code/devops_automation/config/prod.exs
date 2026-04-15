import Config

config :devops_automation, DevopsAutomationWeb.Endpoint,
  http: [ip: {0, 0, 0, 0}, port: 4000],
  check_origin: false
