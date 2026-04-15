from flask import Flask, jsonify, request
import psycopg2
from psycopg2 import sql
from psycopg2.pool import SimpleConnectionPool