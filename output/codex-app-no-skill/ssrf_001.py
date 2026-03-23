import argparse
import ipaddress
import socket
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional
from urllib import error, parse, request