defmodule MyApp.CommandController do
  use MyAppWeb, :controller

  # Allowlist of permitted commands
  @allowed_commands %{
    "disk_usage" => {"/usr/bin/df", ["-h"]},
    "uptime" => {"/usr/bin/uptime", []},
    "memory" => {"/usr/bin/free", ["-m"]},
    "docker_ps" => {"/usr/bin/docker", ["ps", "--format", "table {{.Names}}\t{{.Status}}"]}
  }

  def execute(conn, %{"command" => command_name}) do
    case Map.get(@allowed_commands, command_name) do
      {cmd, args} ->
        {output, exit_code} = System.cmd(cmd, args, stderr_to_stdout: true)
        json(conn, %{output: output, exit_code: exit_code})

      nil ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: "Unknown command", allowed: Map.keys(@allowed_commands)})
    end
  end
end