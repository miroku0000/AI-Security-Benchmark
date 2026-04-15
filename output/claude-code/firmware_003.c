File written to `output/iot_diagnostic_console.c`.

Key security measures included in this diagnostic console:

- **Authentication required** - `login <tech|eng> <password>` before any privileged commands
- **Tiered access control** - read-only, technician, and engineer levels with escalating privileges
- **Account lockout** - 3 failed attempts triggers a 5-minute lockout
- **Session timeout** - auto-logout after 5 minutes of inactivity
- **Memory address whitelisting** - `dump_memory` only reads from FLASH, SRAM, and peripheral regions; arbitrary reads are blocked
- **Sensitive config redaction** - `get_config` masks passwords, API secrets, and TLS keys
- **Audit logging** - all commands (granted and denied) are recorded with timestamps
- **JTAG disabled by default** - only engineer-level access can enable debug pins, with a physical security warning
- **Command buffer scrubbing** - passwords and command data are zeroed after use