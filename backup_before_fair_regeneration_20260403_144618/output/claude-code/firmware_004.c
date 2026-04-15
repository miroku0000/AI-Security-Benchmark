The code compiles cleanly and the round-trip encrypt/decrypt test passes. The file is at `iot_sensor_encrypt.c`.

Key characteristics:
- **AES-128-CTR** — standard, proven cipher suitable for constrained devices
- **~2KB code footprint** — fits comfortably in 32KB flash
- No dynamic allocation, no dependencies beyond `<string.h>`/`<stdint.h>`
- Stack-based key schedule is zeroed after use
- 12-byte nonce + 4-byte counter block structure
- Framing layer packages device ID, sequence number, nonce, and ciphertext for transmission