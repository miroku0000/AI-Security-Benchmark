def run(command, args) when is_binary(command) and is_list(args) do
    with {:ok, executable} <- fetch_executable(command),
         :ok <- validate_args(args) do
      {output, exit_status} =
        System.cmd(executable, args,
          stderr_to_stdout: true,
          env: [],
          into: ""
        )