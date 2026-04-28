I can’t provide runnable code for a Phoenix endpoint/service that takes user-supplied command text from controller params and executes it with `System.cmd("sh", ["-c", ...])`, because that creates an arbitrary remote command execution path.

If you want, I can provide a safe Elixir/Phoenix implementation that uses an allowlist of permitted operations and calls `System.cmd/3` without a shell.