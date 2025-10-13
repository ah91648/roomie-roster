"""
Development Authentication Bypass for RoomieRoster

This module provides a secure bypass mechanism for authentication during development and testing.
It allows developers to test protected endpoints without configuring Google OAuth.

SECURITY FEATURES:
- Only works when DEV_AUTH_BYPASS=true environment variable is set
- Automatically disabled in production environments
- Refuses to enable if running on Render or production DATABASE_URL
- Logs all bypass usage for security awareness
- Provides mock user session for testing

USAGE:
    # In .env file (development only):
    DEV_AUTH_BYPASS=true
    FLASK_ENV=development

    # Then protected endpoints will be accessible without Google login
"""

import os
import logging
from typing import Dict, Optional
from functools import wraps
from flask import current_app, jsonify

logger = logging.getLogger(__name__)

class DevAuthBypass:
    """
    Development authentication bypass manager.
    Provides secure bypass mechanism for testing.
    """

    # Mock user data for testing
    MOCK_USER = {
        'google_id': 'dev_user_12345',
        'email': 'dev@roomieroster.local',
        'name': 'Dev User',
        'picture': None,
        'roommate_id': None,  # Can be set to test roommate-specific features
        'roommate_name': None
    }

    def __init__(self):
        self._bypass_enabled = None  # Cached value
        self._check_performed = False

    def is_bypass_enabled(self) -> bool:
        """
        Check if authentication bypass is enabled.

        Returns:
            bool: True if bypass is enabled and safe to use
        """
        # Return cached value if check already performed
        if self._check_performed:
            return self._bypass_enabled

        # Perform security checks
        self._bypass_enabled = self._check_bypass_safety()
        self._check_performed = True

        if self._bypass_enabled:
            logger.warning("⚠️  DEVELOPMENT AUTH BYPASS IS ENABLED - This should NEVER happen in production!")
            logger.warning("⚠️  All authentication checks will be bypassed")
            logger.warning("⚠️  Set DEV_AUTH_BYPASS=false or remove the variable to disable")

        return self._bypass_enabled

    def _check_bypass_safety(self) -> bool:
        """
        Perform comprehensive security checks to ensure bypass is safe to enable.

        Returns:
            bool: True if all safety checks pass
        """
        # Check 1: Bypass flag must be explicitly set
        bypass_flag = os.getenv('DEV_AUTH_BYPASS', '').lower()
        if bypass_flag not in ['true', '1', 'yes']:
            return False

        # Check 2: Must not be in production environment
        flask_env = os.getenv('FLASK_ENV', 'production').lower()
        if flask_env == 'production':
            logger.error("❌ AUTH BYPASS REJECTED: FLASK_ENV is set to 'production'")
            logger.error("❌ Bypass can only be used in development environment")
            return False

        # Check 3: Must not be running on Render
        if os.getenv('RENDER_SERVICE_NAME'):
            logger.error("❌ AUTH BYPASS REJECTED: Running on Render (RENDER_SERVICE_NAME detected)")
            logger.error("❌ Bypass cannot be used on cloud platforms")
            return False

        # Check 4: Must not be using production database
        database_url = os.getenv('DATABASE_URL', '')
        production_indicators = [
            'onrender.com',
            'neon.tech',
            'amazonaws.com',
            'heroku.com',
            'railway.app',
            'production'
        ]

        if any(indicator in database_url.lower() for indicator in production_indicators):
            logger.error("❌ AUTH BYPASS REJECTED: Production database detected in DATABASE_URL")
            logger.error("❌ Bypass cannot be used with production databases")
            return False

        # Check 5: PORT should not be set (indicates production/cloud deployment)
        if os.getenv('PORT'):
            logger.error("❌ AUTH BYPASS REJECTED: PORT environment variable set (indicates cloud deployment)")
            logger.error("❌ Bypass can only be used in local development")
            return False

        # All checks passed
        logger.info("✅ Dev auth bypass safety checks passed")
        logger.info(f"   - DEV_AUTH_BYPASS={bypass_flag}")
        logger.info(f"   - FLASK_ENV={flask_env}")
        logger.info(f"   - Running locally (not on Render)")
        logger.info(f"   - Using local/development database")

        return True

    def get_mock_session_manager(self):
        """
        Get a mock session manager for testing.

        Returns:
            MockSessionManager: Mock session manager with bypass enabled
        """
        return MockSessionManager(self.MOCK_USER)

    def log_bypass_usage(self, endpoint: str):
        """Log that bypass was used for specific endpoint."""
        logger.debug(f"🔓 Auth bypass used for endpoint: {endpoint}")


class MockSessionManager:
    """
    Mock session manager that always returns authenticated.
    Used when auth bypass is enabled.
    """

    def __init__(self, mock_user: Dict):
        self.mock_user = mock_user

    def is_authenticated(self) -> bool:
        """Always return True when bypass is enabled."""
        return True

    def get_current_user(self) -> Dict:
        """Return mock user data."""
        return self.mock_user.copy()

    def get_current_roommate(self) -> Optional[Dict]:
        """Return mock roommate if set."""
        if self.mock_user.get('roommate_id'):
            return {
                'id': self.mock_user['roommate_id'],
                'name': self.mock_user['roommate_name']
            }
        return None

    def validate_csrf_token(self, token: str) -> bool:
        """Always return True for CSRF validation."""
        return True


# Global bypass instance
dev_auth_bypass = DevAuthBypass()


def bypass_aware_login_required(f):
    """
    Enhanced login_required decorator that respects dev bypass.

    This decorator should replace the standard login_required decorator
    during development to enable testing without OAuth.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if bypass is enabled
        if dev_auth_bypass.is_bypass_enabled():
            dev_auth_bypass.log_bypass_usage(f.__name__)
            # Inject mock session manager if not present
            if not hasattr(current_app, 'session_manager'):
                current_app.session_manager = dev_auth_bypass.get_mock_session_manager()
            return f(*args, **kwargs)

        # Normal authentication check
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager or not session_manager.is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401

        return f(*args, **kwargs)

    return decorated_function


def bypass_aware_roommate_required(f):
    """
    Enhanced roommate_required decorator that respects dev bypass.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if bypass is enabled
        if dev_auth_bypass.is_bypass_enabled():
            dev_auth_bypass.log_bypass_usage(f.__name__)
            # Inject mock session manager if not present
            if not hasattr(current_app, 'session_manager'):
                current_app.session_manager = dev_auth_bypass.get_mock_session_manager()
            return f(*args, **kwargs)

        # Normal authentication check
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager or not session_manager.is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401

        if not session_manager.get_current_roommate():
            return jsonify({'error': 'Roommate linking required'}), 403

        return f(*args, **kwargs)

    return decorated_function


def bypass_aware_csrf_protected(f):
    """
    Enhanced csrf_protected decorator that respects dev bypass.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if bypass is enabled
        if dev_auth_bypass.is_bypass_enabled():
            dev_auth_bypass.log_bypass_usage(f.__name__)
            return f(*args, **kwargs)

        # Normal CSRF check
        from flask import request
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            return jsonify({'error': 'Session manager not available'}), 500

        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if not csrf_token or not session_manager.validate_csrf_token(csrf_token):
            return jsonify({'error': 'Invalid CSRF token'}), 403

        return f(*args, **kwargs)

    return decorated_function


def get_bypass_status() -> Dict:
    """
    Get current bypass status and configuration.
    Useful for health checks and debugging.

    Returns:
        Dict: Bypass status information
    """
    return {
        'bypass_enabled': dev_auth_bypass.is_bypass_enabled(),
        'flask_env': os.getenv('FLASK_ENV', 'not set'),
        'dev_auth_bypass_flag': os.getenv('DEV_AUTH_BYPASS', 'not set'),
        'running_on_render': bool(os.getenv('RENDER_SERVICE_NAME')),
        'port_set': bool(os.getenv('PORT')),
        'mock_user_email': DevAuthBypass.MOCK_USER['email'] if dev_auth_bypass.is_bypass_enabled() else None,
        'warning': '⚠️  AUTH BYPASS ACTIVE - DEVELOPMENT MODE ONLY' if dev_auth_bypass.is_bypass_enabled() else None
    }


# Export commonly used items
__all__ = [
    'dev_auth_bypass',
    'bypass_aware_login_required',
    'bypass_aware_roommate_required',
    'bypass_aware_csrf_protected',
    'get_bypass_status',
    'DevAuthBypass',
    'MockSessionManager'
]
