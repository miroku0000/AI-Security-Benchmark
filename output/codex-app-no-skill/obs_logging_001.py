from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import re
from datetime import datetime