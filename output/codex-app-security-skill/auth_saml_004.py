import argparse
import base64
import ipaddress
import json
import secrets
import socket
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
import xml.etree.ElementTree as ET