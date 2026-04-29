I cannot and will not provide code that uses `Marshal.load` on untrusted user input from cookies. This creates a critical remote code execution vulnerability, as `Marshal.load` can execute arbitrary Ruby code during deserialization.

For secure Rails session management, use Rails' built-in encrypted cookie store or a database-backed session store instead.