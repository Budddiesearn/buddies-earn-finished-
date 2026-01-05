from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
import os

db = SQLAlchemy()
DB_NAME = "database.db"


def create_app(config_overrides=None):
    app = Flask(__name__)

    # Base configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'BUDDIES EARN')

    # Use PostgreSQL in production, SQLite in development
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Render uses postgresql://, but SQLAlchemy needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace(
                'postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    # Allow tests or other callers to override settings (e.g., in-memory DB)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)

    from .views import views
    from .auth import auth
    from .admin import admin

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(admin)

    from .models import User, Note

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    # Create all tables for the configured database URI (works for in-memory too)
    with app.app_context():
        db.create_all()
