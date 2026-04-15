@spec execute(term(), term()) ::
          {:ok, %{command: String.t(), exit_status: non_neg_integer(), stdout: String.t()}}
          | {:error, %{status: pos_integer(), error: String.t()}}
  def execute(command_name, args) do
    with {:ok, validated_command} <- validate_command_name(command_name),
         {:ok, validated_args} <- validate_args(args),
         {:ok, spec} <- CommandPolicy.fetch_command(validated_command),
         :ok <- ensure_extra_args_allowed(spec, validated_args),
         {:ok, executable} <- CommandPolicy.resolve_executable(spec),
         final_args = spec.base_args ++ validated_args,
         {:ok, output, exit_status} <- run_command(executable, final_args, spec.timeout_ms) do
      {:ok, %{command: validated_command, exit_status: exit_status, stdout: output}}
    else
      {:error, :invalid_command} ->
        {:error, %{status: 400, error: "invalid command parameter"}}