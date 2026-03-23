from flask import Flask, abort, jsonify, make_response
from flask_login import LoginManager, UserMixin, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.middleware.proxy_fix import ProxyFix