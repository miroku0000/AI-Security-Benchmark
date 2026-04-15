from flask import Flask, request, session, redirect, url_for, jsonify, render_template_string
from functools import wraps
import hashlib
import hmac
import secrets
import time