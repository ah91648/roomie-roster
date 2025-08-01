import os
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth.exceptions
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    # Define Credentials as None if not available to prevent NameError
    Credentials = None

class AuthService:
    """Google Authentication service for RoomieRoster user login."""
    
    # OAuth scopes for user authentication, profile access, and calendar integration
    SCOPES = [
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events',
        'openid'
    ]
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.auth_credentials_file = self.data_dir / "google_auth_credentials.json"
        self.auth_tokens_file = self.data_dir / "google_auth_tokens.json"
        self.is_available = GOOGLE_AVAILABLE
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        if not self.is_available:
            print("Google Auth API dependencies not available. Install with: pip install -r requirements.txt")
    
    def is_configured(self) -> bool:
        """Check if Google Authentication is properly configured."""
        if not self.is_available:
            return False
        # Check if configured via environment variables or credentials file
        return (os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET')) or self.auth_credentials_file.exists()
    
    def _get_credentials_config(self) -> Dict:
        """Get credentials configuration from environment variables or file."""
        # First try environment variables (preferred for production)
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if client_id and client_secret:
            return {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
            }
        
        # Fall back to credentials file
        if self.auth_credentials_file.exists():
            with open(self.auth_credentials_file, 'r') as f:
                return json.load(f)
        
        return None

    def setup_credentials(self, credentials_json: Dict) -> Dict:
        """Set up Google Authentication credentials from JSON data."""
        if not self.is_available:
            raise Exception("Google Auth API dependencies not installed")
        
        try:
            # Validate that this is a valid OAuth client credentials file
            if 'web' not in credentials_json and 'installed' not in credentials_json:
                raise ValueError("Invalid credentials format. Must be OAuth 2.0 client credentials.")
            
            # Save credentials to file
            with open(self.auth_credentials_file, 'w') as f:
                json.dump(credentials_json, f, indent=2)
            
            return {"message": "Authentication credentials saved successfully."}
        except Exception as e:
            raise Exception(f"Failed to save auth credentials: {str(e)}")
    
    def get_auth_url(self, redirect_uri: str, state: str = None) -> str:
        """Get OAuth authorization URL for user login."""
        if not self.is_available:
            raise Exception("Google Auth API dependencies not installed")
        
        credentials_config = self._get_credentials_config()
        if not credentials_config:
            raise Exception("Auth credentials not found. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables or upload credentials file.")
        
        try:
            # Create flow from credentials configuration
            flow = Flow.from_client_config(
                credentials_config, 
                scopes=self.SCOPES
            )
            flow.redirect_uri = redirect_uri
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state or secrets.token_urlsafe(32),
                prompt='consent'  # Force consent to ensure refresh token
            )
            
            return auth_url
        except Exception as e:
            raise Exception(f"Failed to generate auth URL: {str(e)}")
    
    def handle_auth_callback(self, authorization_code: str, redirect_uri: str, state: str = None) -> Dict:
        """Handle OAuth callback and exchange code for tokens."""
        if not self.is_available:
            raise Exception("Google Auth API dependencies not installed")
        
        credentials_config = self._get_credentials_config()
        if not credentials_config:
            raise Exception("Auth credentials not found. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables or upload credentials file.")
        
        try:
            # Create flow from credentials configuration
            flow = Flow.from_client_config(
                credentials_config, 
                scopes=self.SCOPES
            )
            flow.redirect_uri = redirect_uri
            
            # Exchange authorization code for tokens
            flow.fetch_token(code=authorization_code)
            
            # Get user info
            user_info = self._get_user_info(flow.credentials)
            
            # Store tokens securely
            token_data = {
                'google_id': user_info['id'],
                'email': user_info['email'],
                'name': user_info['name'],
                'picture': user_info.get('picture'),
                'credentials': flow.credentials.to_json(),
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat()
            }
            
            self._save_user_token(user_info['id'], token_data)
            
            return {
                'user': {
                    'google_id': user_info['id'],
                    'email': user_info['email'], 
                    'name': user_info['name'],
                    'picture': user_info.get('picture')
                },
                'message': 'Authentication successful'
            }
        except Exception as e:
            raise Exception(f"Authentication callback failed: {str(e)}")
    
    def _get_user_info(self, credentials) -> Dict:
        """Get user profile information from Google."""
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            return user_info
        except Exception as e:
            raise Exception(f"Failed to get user info: {str(e)}")
    
    def _save_user_token(self, google_id: str, token_data: Dict) -> None:
        """Save user token data securely."""
        try:
            # Load existing tokens
            tokens = {}
            if self.auth_tokens_file.exists():
                with open(self.auth_tokens_file, 'r') as f:
                    tokens = json.load(f)
            
            # Update with new token data
            tokens[google_id] = token_data
            
            # Save back to file
            with open(self.auth_tokens_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Set restrictive permissions on token file
            os.chmod(self.auth_tokens_file, 0o600)
            
        except Exception as e:
            raise Exception(f"Failed to save user token: {str(e)}")
    
    def get_user_by_google_id(self, google_id: str) -> Optional[Dict]:
        """Get user data by Google ID."""
        try:
            if not self.auth_tokens_file.exists():
                return None
            
            with open(self.auth_tokens_file, 'r') as f:
                tokens = json.load(f)
            
            user_data = tokens.get(google_id)
            if not user_data:
                return None
            
            # Update last login
            user_data['last_login'] = datetime.now().isoformat()
            self._save_user_token(google_id, user_data)
            
            return {
                'google_id': user_data['google_id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'picture': user_data.get('picture'),
                'last_login': user_data['last_login']
            }
        except Exception as e:
            raise Exception(f"Failed to get user: {str(e)}")
    
    def refresh_user_token(self, google_id: str) -> bool:
        """Refresh user's access token."""
        try:
            if not self.auth_tokens_file.exists():
                return False
            
            with open(self.auth_tokens_file, 'r') as f:
                tokens = json.load(f)
            
            user_data = tokens.get(google_id)
            if not user_data:
                return False
            
            # Load credentials and refresh
            creds = Credentials.from_authorized_user_info(
                json.loads(user_data['credentials']), 
                self.SCOPES
            )
            
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                
                # Update stored credentials
                user_data['credentials'] = creds.to_json()
                user_data['last_token_refresh'] = datetime.now().isoformat()
                self._save_user_token(google_id, user_data)
                
                return True
            
            return True  # Token was still valid
            
        except Exception as e:
            print(f"Failed to refresh token for user {google_id}: {str(e)}")
            return False
    
    def validate_user_token(self, google_id: str) -> bool:
        """Validate that user's token is still valid."""
        try:
            if not self.auth_tokens_file.exists():
                return False
            
            with open(self.auth_tokens_file, 'r') as f:
                tokens = json.load(f)
            
            user_data = tokens.get(google_id)
            if not user_data:
                return False
            
            # Load credentials and check validity
            creds = Credentials.from_authorized_user_info(
                json.loads(user_data['credentials']), 
                self.SCOPES
            )
            
            # Try to refresh if expired
            if creds.expired and creds.refresh_token:
                return self.refresh_user_token(google_id)
            
            return creds.valid
            
        except Exception as e:
            print(f"Failed to validate token for user {google_id}: {str(e)}")
            return False
    
    def revoke_user_token(self, google_id: str) -> bool:
        """Revoke user's access token and remove from storage."""
        try:
            if not self.auth_tokens_file.exists():
                return True
            
            with open(self.auth_tokens_file, 'r') as f:
                tokens = json.load(f)
            
            user_data = tokens.get(google_id)
            if user_data:
                # Try to revoke the token with Google
                try:
                    creds = Credentials.from_authorized_user_info(
                        json.loads(user_data['credentials']), 
                        self.SCOPES
                    )
                    
                    # Revoke token with Google
                    import requests
                    revoke_url = 'https://oauth2.googleapis.com/revoke'
                    requests.post(revoke_url, 
                                params={'token': creds.token},
                                headers={'content-type': 'application/x-www-form-urlencoded'})
                except Exception as e:
                    print(f"Failed to revoke token with Google: {str(e)}")
                
                # Remove from local storage
                del tokens[google_id]
                with open(self.auth_tokens_file, 'w') as f:
                    json.dump(tokens, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Failed to revoke token for user {google_id}: {str(e)}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """Get all authenticated users (for admin purposes)."""
        try:
            if not self.auth_tokens_file.exists():
                return []
            
            with open(self.auth_tokens_file, 'r') as f:
                tokens = json.load(f)
            
            users = []
            for google_id, user_data in tokens.items():
                users.append({
                    'google_id': user_data['google_id'],
                    'email': user_data['email'],
                    'name': user_data['name'],
                    'picture': user_data.get('picture'),
                    'last_login': user_data.get('last_login'),
                    'created_at': user_data.get('created_at')
                })
            
            return users
            
        except Exception as e:
            raise Exception(f"Failed to get users: {str(e)}")
    
    def get_status(self) -> Dict:
        """Get authentication service status."""
        user_count = 0
        if self.auth_tokens_file.exists():
            try:
                with open(self.auth_tokens_file, 'r') as f:
                    tokens = json.load(f)
                    user_count = len(tokens)
            except:
                user_count = 0
        
        return {
            "google_api_available": self.is_available,
            "credentials_configured": self.auth_credentials_file.exists(),
            "total_users": user_count,
            "tokens_file_exists": self.auth_tokens_file.exists()
        }