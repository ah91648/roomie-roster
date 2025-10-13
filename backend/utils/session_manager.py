import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Callable
from flask import session, request, jsonify, current_app
from .auth_service import AuthService
from .data_handler import DataHandler
from .dev_auth_bypass import dev_auth_bypass, get_bypass_status

class SessionManager:
    """Secure session management for RoomieRoster authentication."""
    
    def __init__(self, app=None, auth_service: AuthService = None, data_handler: DataHandler = None):
        self.auth_service = auth_service
        self.data_handler = data_handler
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Flask app with secure session configuration."""
        # Set secret key from environment variable or generate temporary one
        secret_key = os.getenv('FLASK_SECRET_KEY')
        if not app.config.get('SECRET_KEY'):
            if secret_key:
                app.config['SECRET_KEY'] = secret_key
                print("✅ Using SECRET_KEY from environment variable.")
            else:
                app.config['SECRET_KEY'] = secrets.token_hex(32)
                print("Warning: Generated temporary SECRET_KEY. Set FLASK_SECRET_KEY environment variable for production.")
        
        # Session configuration for security
        # Detect production environment (Render sets PORT environment variable)
        is_production = bool(os.getenv('PORT')) or os.getenv('FLASK_ENV') == 'production'
        
        app.config.update({
            'SESSION_COOKIE_SECURE': is_production,  # HTTPS only in production
            'SESSION_COOKIE_HTTPONLY': True,  # Prevent XSS access to session cookie
            'SESSION_COOKIE_SAMESITE': 'Lax',  # CSRF protection
            'PERMANENT_SESSION_LIFETIME': timedelta(days=30),  # Session expiry
            'SESSION_TYPE': 'filesystem',  # Store sessions on filesystem (could upgrade to Redis)
        })
        
        # Store references
        app.session_manager = self
        
        # Register teardown handler for session cleanup
        @app.teardown_appcontext
        def cleanup_session(error):
            if error:
                session.clear()
    
    def create_user_session(self, google_id: str, user_data: Dict, remember_me: bool = True) -> bool:
        """Create a new user session."""
        try:
            # Clear any existing session
            session.clear()
            
            # Set session data
            session['authenticated'] = True
            session['google_id'] = google_id
            session['user_email'] = user_data['email']
            session['user_name'] = user_data['name']
            session['user_picture'] = user_data.get('picture')
            session['login_time'] = datetime.now().isoformat()
            session['csrf_token'] = secrets.token_urlsafe(32)
            
            # Set permanent session if remember me
            session.permanent = remember_me
            
            # Check if user is linked to a roommate
            if self.data_handler:
                linked_roommate = self._get_linked_roommate(google_id)
                if linked_roommate:
                    session['roommate_id'] = linked_roommate['id']
                    session['roommate_name'] = linked_roommate['name']
            
            return True
        except Exception as e:
            print(f"Failed to create session: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if current session is authenticated."""
        return session.get('authenticated', False)
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user data."""
        if not self.is_authenticated():
            return None
        
        user_data = {
            'google_id': session.get('google_id'),
            'email': session.get('user_email'),
            'name': session.get('user_name'),
            'picture': session.get('user_picture'),
            'login_time': session.get('login_time'),
            'csrf_token': session.get('csrf_token')
        }
        
        # Add roommate info if linked
        if session.get('roommate_id'):
            user_data['roommate'] = {
                'id': session.get('roommate_id'),
                'name': session.get('roommate_name')
            }
        
        return user_data
    
    def get_current_roommate(self) -> Optional[Dict]:
        """Get current user's linked roommate."""
        if not self.is_authenticated():
            return None
        
        roommate_id = session.get('roommate_id')
        if not roommate_id or not self.data_handler:
            return None
        
        roommates = self.data_handler.get_roommates()
        return next((r for r in roommates if r['id'] == roommate_id), None)
    
    def link_roommate(self, roommate_id: int) -> bool:
        """Link current user to a roommate."""
        if not self.is_authenticated():
            return False
        
        try:
            google_id = session.get('google_id')
            if not google_id or not self.data_handler:
                return False
            
            # Verify roommate exists
            roommates = self.data_handler.get_roommates()
            roommate = next((r for r in roommates if r['id'] == roommate_id), None)
            if not roommate:
                return False
            
            # Check if roommate is already linked to another account
            if roommate.get('google_id') and roommate['google_id'] != google_id:
                return False
            
            # Update roommate with Google ID
            roommate['google_id'] = google_id
            roommate['google_profile_picture_url'] = session.get('user_picture')
            roommate['linked_at'] = datetime.now().isoformat()
            
            # Save updated roommates
            self.data_handler.save_roommates(roommates)
            
            # Update session
            session['roommate_id'] = roommate['id']
            session['roommate_name'] = roommate['name']
            
            return True
        except Exception as e:
            print(f"Failed to link roommate: {str(e)}")
            return False
    
    def unlink_roommate(self) -> bool:
        """Unlink current user from their roommate."""
        if not self.is_authenticated():
            return False
        
        try:
            google_id = session.get('google_id')
            roommate_id = session.get('roommate_id')
            
            if not google_id or not roommate_id or not self.data_handler:
                return False
            
            # Remove Google ID from roommate
            roommates = self.data_handler.get_roommates()
            roommate = next((r for r in roommates if r['id'] == roommate_id), None)
            if roommate and roommate.get('google_id') == google_id:
                roommate.pop('google_id', None)
                roommate.pop('google_profile_picture_url', None)
                roommate.pop('linked_at', None)
                self.data_handler.save_roommates(roommates)
            
            # Remove from session
            session.pop('roommate_id', None)
            session.pop('roommate_name', None)
            
            return True
        except Exception as e:
            print(f"Failed to unlink roommate: {str(e)}")
            return False
    
    def _get_linked_roommate(self, google_id: str) -> Optional[Dict]:
        """Get roommate linked to Google ID."""
        if not self.data_handler:
            return None
        
        roommates = self.data_handler.get_roommates()
        return next((r for r in roommates if r.get('google_id') == google_id), None)
    
    def clear_session(self) -> bool:
        """Clear current session."""
        try:
            session.clear()
            return True
        except Exception as e:
            print(f"Failed to clear session: {str(e)}")
            return False
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token."""
        return session.get('csrf_token') == token
    
    def refresh_session(self) -> bool:
        """Refresh current session with updated user data."""
        if not self.is_authenticated():
            return False
        
        try:
            google_id = session.get('google_id')
            if not google_id or not self.auth_service:
                return False
            
            # Validate and refresh Google token
            if not self.auth_service.validate_user_token(google_id):
                # Token invalid, clear session
                self.clear_session()
                return False
            
            # Get updated user data
            user_data = self.auth_service.get_user_by_google_id(google_id)
            if not user_data:
                self.clear_session()
                return False
            
            # Update session with fresh data
            session['user_email'] = user_data['email']
            session['user_name'] = user_data['name']
            session['user_picture'] = user_data.get('picture')
            
            # Check roommate linking status
            if self.data_handler:
                linked_roommate = self._get_linked_roommate(google_id)
                if linked_roommate:
                    session['roommate_id'] = linked_roommate['id']
                    session['roommate_name'] = linked_roommate['name']
                else:
                    session.pop('roommate_id', None)
                    session.pop('roommate_name', None)
            
            return True
        except Exception as e:
            print(f"Failed to refresh session: {str(e)}")
            return False

# Decorators for route protection
def login_required(f: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    Supports development bypass when DEV_AUTH_BYPASS=true.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if development bypass is enabled
        if dev_auth_bypass.is_bypass_enabled():
            dev_auth_bypass.log_bypass_usage(f.__name__)
            # Inject mock session manager if not present
            if not hasattr(current_app, 'session_manager') or current_app.session_manager is None:
                current_app.session_manager = dev_auth_bypass.get_mock_session_manager()
            return f(*args, **kwargs)

        # Normal authentication check
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager or not session_manager.is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def roommate_required(f: Callable) -> Callable:
    """
    Decorator to require roommate linking for a route.
    Supports development bypass when DEV_AUTH_BYPASS=true.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if development bypass is enabled
        if dev_auth_bypass.is_bypass_enabled():
            dev_auth_bypass.log_bypass_usage(f.__name__)
            # Inject mock session manager if not present
            if not hasattr(current_app, 'session_manager') or current_app.session_manager is None:
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

def csrf_protected(f: Callable) -> Callable:
    """
    Decorator to require CSRF token for a route.
    Supports development bypass when DEV_AUTH_BYPASS=true.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if development bypass is enabled
        if dev_auth_bypass.is_bypass_enabled():
            dev_auth_bypass.log_bypass_usage(f.__name__)
            return f(*args, **kwargs)

        # Normal CSRF check
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            return jsonify({'error': 'Session manager not available'}), 500

        # Check for CSRF token in headers or form data
        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if not csrf_token or not session_manager.validate_csrf_token(csrf_token):
            return jsonify({'error': 'Invalid CSRF token'}), 403

        return f(*args, **kwargs)
    return decorated_function