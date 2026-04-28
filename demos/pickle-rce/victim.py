"""Victim runs the AI-generated load_from_file().

This is the harness side. The vulnerability lives in the imported
victim_module — a verbatim copy of output/gpt-4/deserial_001.py. This
script just instantiates the class and calls the method, mirroring
how the AI-generated code would be used in a real "load preferences
on login" code path.
"""

import os
import sys

# Local import — victim_module.py is in this same directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from victim_module import UserPreference  # noqa: E402  (intentional path setup above)


def main():
    pkl_path = os.getenv("PICKLE_OUT", "preferences.pkl")
    prefs = UserPreference(preference_data=None)
    print(f"Victim: about to call AI-generated load_from_file({pkl_path!r})...")
    prefs.load_from_file(pkl_path)
    print(f"Victim: load_from_file returned. preference_data = {prefs.preference_data!r}")


if __name__ == "__main__":
    main()
