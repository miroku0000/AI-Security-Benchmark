import errno
import os
import sqlite3
import stat
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional