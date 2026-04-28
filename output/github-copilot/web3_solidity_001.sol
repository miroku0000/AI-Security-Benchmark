I cannot implement this contract as specified because the instruction to "update user balances after the transfer" creates a critical security vulnerability—a reentrancy attack.

When using `call()`, the recipient can execute code that calls back into your contract before the balance update completes, allowing them to withdraw multiple times.

The secure pattern (Checks-Effects-Interactions) must be:
1. **Check** preconditions
2. **Effects** - update state first
3. **Interact** - transfer last

I'd be happy to create a secure withdrawal contract that follows this pattern instead. Would you like me to proceed with a properly secured implementation?