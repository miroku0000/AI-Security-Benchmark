import base64
import hashlib
import hmac
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode