import base64
import hashlib
import hmac
import io
import json
import secrets
import sqlite3
import sys
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path