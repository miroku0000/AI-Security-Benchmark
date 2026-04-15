import os
import time
from flask import Flask, Response, jsonify, request, g
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST