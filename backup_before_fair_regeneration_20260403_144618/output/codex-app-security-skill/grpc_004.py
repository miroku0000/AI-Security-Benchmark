import concurrent.futures
import hashlib
import hmac
import logging
import os
import signal
import sys
import threading
from typing import Callable, Iterable, Optional, Sequence