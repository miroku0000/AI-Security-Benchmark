defmodule SqlQueryApp.MixProject do
  use Mix.Project

  def project do
    [
      app: :sql_query_app,
      version: "0.1.0",
      elixir: "~> 1.14",
      deps: deps()
    ]
  end

  def application do
    [extra_applications: [:logger], mod: {SqlQueryApp.Application, []}]
  end

  defp deps do
    [
      {:ecto_sql, "~> 3.10"},
      {:postgrex, ">= 0.0.0"}
    ]
  end
end
