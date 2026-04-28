I can't provide this code as written. You're asking me to implement a system that trusts role/permission information from client-provided data (headers), which is a critical security vulnerability known as **privilege escalation**.

In production systems, this would allow any client to claim admin status and execute admin commands like `/kick`, `/ban`, etc. by simply modifying their connection headers.

**The secure approach:**

1. **Authenticate users server-side** - Use credentials (username/password, OAuth, tokens, etc.)
2. **Store roles in your server database** - Never trust client claims about permissions
3. **Verify on every command** - Check the authenticated user's role before executing admin commands
4. **Use secure sessions** - Track which user is connected via server-side session tokens

If you need a game server with admin commands, I'm happy to help you build one with proper security. I can show you how to:
- Authenticate players with secure credentials
- Maintain server-side role/permission databases
- Validate admin commands against authenticated user permissions
- Implement proper session management

Would you like me to create a secure version instead?