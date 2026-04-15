import os
import imghdr
import uuid
from flask import Flask, jsonify, request, send_from_directory, url_for
from werkzeug.utils import secure_filename