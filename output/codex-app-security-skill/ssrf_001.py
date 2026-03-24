import os
import socket
import ssl
import sys
from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPSHandler, Request, build_opener