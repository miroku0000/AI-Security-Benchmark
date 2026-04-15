import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from email.utils import parseaddr
from threading import Lock
from typing import Any, Dict, Optional