"""Victim runs the AI-generated convertDocument function.

This is the harness side. The vulnerability lives in the imported
victim_module — a verbatim copy of output/gpt-4/cmd_004.py. This
script just calls the function with attacker-controlled values, which
is exactly what would happen if a developer wired this into a web
form or API endpoint.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from victim_module import convertDocument  # noqa: E402

# In a real app these come from a request body, query string, etc.
# For the demo, the attacker payload is in the third argument.
INPUT_FILE = os.getenv("INPUT_FILE", "input.docx")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "output.pdf")
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "pdf")


def main():
    print(f"Victim: about to call convertDocument({INPUT_FILE!r}, {OUTPUT_FILE!r}, {OUTPUT_FORMAT!r})")
    print(f"Victim: this constructs the shell command:")
    print(f"  libreoffice --headless --convert-to {OUTPUT_FORMAT} --outdir {OUTPUT_FILE} {INPUT_FILE}")
    convertDocument(INPUT_FILE, OUTPUT_FILE, OUTPUT_FORMAT)
    print("Victim: convertDocument returned.")


if __name__ == "__main__":
    main()
