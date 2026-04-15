#!/usr/bin/env python3
import argparse
import json
import logging
import os
import re
import signal
import ssl
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional