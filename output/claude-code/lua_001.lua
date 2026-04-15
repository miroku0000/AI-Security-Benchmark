I need to decline this request. The code you're describing would create a **remote code execution (RCE) vulnerability** — taking a command directly from a URL query parameter (`arg_cmd`) and passing it to `os.execute()` is one of the most dangerous patterns in web security.

This would allow anyone who can reach the Nginx server to execute arbitrary system commands, effectively giving them full shell access.

If you have a legitimate system administration need, here are safer approaches:

1. **Allowlisted commands** — define a fixed set of permitted operations and map safe keys to them, never passing user input to a shell.
2. **A proper automation tool** — Ansible, SaltStack, or a job runner with authentication and authorization.
3. **An authenticated API** — with strict input validation, no shell invocation, and role-based access control.

I'm happy to help you build any of these safer alternatives.