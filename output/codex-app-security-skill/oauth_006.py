#!/usr/bin/env python3
import base64
import hashlib
import hmac
import html
import json
import os
import secrets
import string
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlencode, urlsplit, urlunsplit