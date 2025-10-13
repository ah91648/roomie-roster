"""
Pytest configuration and fixtures for RoomieRoster tests.
"""
import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import from utils
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    from flask import Flask

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    # Initialize database for testing
    from utils.database_config import db
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner for the Flask application."""
    return app.test_cli_runner()
