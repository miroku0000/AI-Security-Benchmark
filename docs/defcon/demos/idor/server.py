"""Server harness for the IDOR demo.

Imports the verbatim AI-generated download_invoice() route from
victim_module and runs it on a non-default port. The harness only adds
the listening configuration — the route definition is the AI's.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from victim_module import app  # noqa: E402  (path setup above)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5093"))
    app.run(host="127.0.0.1", port=port, debug=False)
