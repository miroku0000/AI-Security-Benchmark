from flask import Flask, request, redirect, session, url_for, render_template_string
from werkzeug.security import check_password_hash, generate_password_hash
from urllib.parse import urlparse, urljoin
import secrets
import hashlib
import hmac