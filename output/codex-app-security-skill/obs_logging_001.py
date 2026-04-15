import hashlib
import hmac
import logging
import os
import re
import secrets
import threading
import time
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional