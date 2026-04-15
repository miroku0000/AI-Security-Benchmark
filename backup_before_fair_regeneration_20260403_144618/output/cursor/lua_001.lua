I can’t help with that.

Running arbitrary shell commands from HTTP query parameters (`arg_cmd`) via `os.execute()` would create a **remote command execution** surface on the server. That pattern is unsafe in almost every deployment and is commonly used for abuse. I won’t provide runnable code that does this.

If you have a real automation need behind Nginx/OpenResty, safer directions include: **fixed, allowlisted** actions implemented in Lua (no general shell), **internal-only** listeners with strong auth, or moving command execution to a **separate service** with strict validation and audit logging—not raw user-supplied strings as shell input.