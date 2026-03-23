from flask import Flask, jsonify
from flask_login import LoginManager, UserMixin, current_user, login_required
from flask_sqlalchemy import SQLAlchemy