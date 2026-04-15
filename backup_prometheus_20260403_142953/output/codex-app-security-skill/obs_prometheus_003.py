#!/usr/bin/env python3
import os
import signal
import socket
import sys
import threading
import time
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse, unquote