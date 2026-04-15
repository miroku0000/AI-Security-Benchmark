import Config

config :sql_query_app, SqlQueryApp.Repo,
  database: "sql_query_app_dev",
  username: "postgres",
  password: "postgres",
  hostname: "localhost"

config :sql_query_app, ecto_repos: [SqlQueryApp.Repo]
