#!/usr/bin/env python3
"""
Script to create a test session cookie for Selenium testing.
This allows bypassing Google OAuth for automated testing.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
project_root = backend_dir.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

from flask import Flask
from flask.sessions import SecureCookieSessionInterface
from itsdangerous import URLSafeTimedSerializer
from utils.database_config import database_config, db
from models.models import Roommate, GoogleUser

def create_test_session():
    """Create a test session cookie for an existing roommate."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'test-secret-key')
    app.config['SESSION_COOKIE_NAME'] = 'session'

    # Configure database
    database_config.configure_flask_app(app)

    with app.app_context():
        # Get first roommate
        roommate = Roommate.query.first()
        if not roommate:
            print("ERROR: No roommates found in database")
            return None

        print(f"Found roommate: {roommate.name} (ID: {roommate.id})")

        # Check if roommate has a linked Google user
        google_user = GoogleUser.query.filter_by(roommate_id=roommate.id).first()

        if not google_user:
            # Create a test Google user linked to this roommate
            google_user = GoogleUser(
                google_id=f"test_google_id_{roommate.id}",
                email=f"test{roommate.id}@example.com",
                name=roommate.name,
                picture="https://example.com/avatar.jpg",
                roommate_id=roommate.id
            )
            db.session.add(google_user)
            db.session.commit()
            print(f"Created test Google user: {google_user.email}")
        else:
            print(f"Found existing Google user: {google_user.email}")

        # Create session data
        session_data = {
            'user_id': google_user.id,
            'google_id': google_user.google_id,
            'email': google_user.email,
            'name': google_user.name,
            'roommate_id': roommate.id,
            'roommate_name': roommate.name
        }

        # Sign the session
        serializer = URLSafeTimedSerializer(
            app.config['SECRET_KEY'],
            salt='cookie-session',
            serializer=app.session_interface.get_signing_serializer(app)._serializer
        )

        session_cookie = app.session_interface.get_signing_serializer(app).dumps(session_data)

        print(f"\n=== TEST SESSION CREATED ===")
        print(f"Roommate: {roommate.name}")
        print(f"Email: {google_user.email}")
        print(f"Roommate ID: {roommate.id}")
        print(f"\nSession Cookie:")
        print(session_cookie)
        print(f"\n=== USE THIS COOKIE IN SELENIUM ===")

        return {
            'cookie_value': session_cookie,
            'cookie_name': 'session',
            'roommate_id': roommate.id,
            'roommate_name': roommate.name,
            'email': google_user.email
        }

if __name__ == '__main__':
    result = create_test_session()
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
