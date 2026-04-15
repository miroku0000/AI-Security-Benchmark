import argparse
import csv
import hashlib
import json
import math
import os
import sqlite3
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple