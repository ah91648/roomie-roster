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
    
    def get_user_credentials(self, google_id: str) -> Optional[Credentials]:
        """Get Google credentials for a specific user."""
        try:
            if not self.auth_tokens_file.exists():
                return None
            
            with open(self.auth_tokens_file, 'r') as f:
                tokens = json.load(f)
            
            user_data = tokens.get(google_id)
            if not user_data:
                return None
            
            # Load credentials
            creds = Credentials.from_authorized_user_info(
                json.loads(user_data['credentials']), 
                self.SCOPES
            )
            
            # Refresh if needed
            if creds.expired and creds.refresh_token:
                if self.refresh_user_token(google_id):
                    # Reload the refreshed credentials
                    with open(self.auth_tokens_file, 'r') as f:
                        updated_tokens = json.load(f)
                    updated_user_data = updated_tokens.get(google_id)
                    if updated_user_data:
                        creds = Credentials.from_authorized_user_info(
                            json.loads(updated_user_data['credentials']), 
                            self.SCOPES
                        )
            
            return creds if creds.valid else None
            
        except Exception as e:
            print(f"Failed to get credentials for user {google_id}: {str(e)}")
            return None
    
    def validate_calendar_access(self, google_id: str) -> Dict:
        """
        Validate that a user has proper calendar access permissions.
        Returns detailed status of calendar-related permissions.
        """
        try:
            creds = self.get_user_credentials(google_id)
            if not creds:
                return {
                    "valid": False,
                    "error": "No valid credentials found",
                    "calendar_access": False,
                    "scopes_granted": []
                }
            
            # Check if required calendar scopes are present
            required_calendar_scopes = [
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/calendar.events'
            ]
            
            granted_scopes = creds.scopes or []
            missing_scopes = [scope for scope in required_calendar_scopes if scope not in granted_scopes]
            
            # Test actual calendar access by attempting to list calendars
            calendar_access_test = False
            calendar_count = 0
            try:
                service = build('calendar', 'v3', credentials=creds)
                calendars_result = service.calendarList().list().execute()
                calendar_count = len(calendars_result.get('items', []))
                calendar_access_test = True
            except Exception as e:
                print(f"Calendar access test failed for user {google_id}: {str(e)}")
            
            return {
                "valid": len(missing_scopes) == 0 and calendar_access_test,
                "calendar_access": calendar_access_test,
                "calendar_count": calendar_count,
                "scopes_granted": granted_scopes,
                "missing_scopes": missing_scopes,
                "credentials_valid": creds.valid,
                "credentials_expired": creds.expired,
                "has_refresh_token": bool(creds.refresh_token)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation failed: {str(e)}",
                "calendar_access": False,
                "scopes_granted": []
            }
    
    def get_linked_roommates(self) -> List[Dict]:
        """
        Get all roommates that are linked to Google accounts.
        Combines roommate data with authentication status.
        """
        try:
            # Load roommates data
            roommates_file = self.data_dir / "roommates.json"
            if not roommates_file.exists():
                return []
            
            with open(roommates_file, 'r') as f:
                roommates = json.load(f)
            
            linked_roommates = []
            
            for roommate in roommates:
                google_id = roommate.get('google_id')
                if not google_id:
                    continue
                
                # Get authentication status
                auth_status = self.validate_user_token(google_id)
                calendar_status = self.validate_calendar_access(google_id) if auth_status else {
                    "valid": False, "calendar_access": False
                }
                
                # Get user info if available
                user_info = self.get_user_by_google_id(google_id)
                
                linked_roommates.append({
                    'roommate_id': roommate['id'],
                    'roommate_name': roommate['name'],
                    'google_id': google_id,
                    'linked_at': roommate.get('linked_at'),
                    'auth_valid': auth_status,
                    'calendar_access': calendar_status.get('calendar_access', False),
                    'calendar_count': calendar_status.get('calendar_count', 0),
                    'user_email': user_info.get('email') if user_info else None,
                    'last_login': user_info.get('last_login') if user_info else None,
                    'missing_scopes': calendar_status.get('missing_scopes', [])
                })
            
            return linked_roommates
            
        except Exception as e:
            print(f"Error getting linked roommates: {str(e)}")
            return []
    
    def link_roommate_to_google_account(self, roommate_id: int, google_id: str) -> Dict:
        """
        Link a roommate to a Google account.
        Updates the roommate record with Google account information.
        """
        try:
            # Validate that the Google account exists and has proper access
            user_info = self.get_user_by_google_id(google_id)
            if not user_info:
                return {"success": False, "error": "Google account not found or not authenticated"}
            
            calendar_status = self.validate_calendar_access(google_id)
            if not calendar_status.get('calendar_access', False):
                return {
                    "success": False, 
                    "error": "Google account does not have proper calendar access",
                    "details": calendar_status
                }
            
            # Load roommates data
            roommates_file = self.data_dir / "roommates.json"
            if not roommates_file.exists():
                return {"success": False, "error": "Roommates data not found"}
            
            with open(roommates_file, 'r') as f:
                roommates = json.load(f)
            
            # Find the roommate
            roommate_found = False
            for roommate in roommates:
                if roommate['id'] == roommate_id:
                    # Check if this Google account is already linked to another roommate
                    for other_roommate in roommates:
                        if (other_roommate['id'] != roommate_id and 
                            other_roommate.get('google_id') == google_id):
                            return {
                                "success": False, 
                                "error": f"Google account already linked to {other_roommate['name']}"
                            }
                    
                    # Link the account
                    roommate['google_id'] = google_id
                    roommate['google_profile_picture_url'] = user_info.get('picture')
                    roommate['linked_at'] = datetime.now().isoformat()
                    roommate_found = True
                    break
            
            if not roommate_found:
                return {"success": False, "error": f"Roommate with ID {roommate_id} not found"}
            
            # Save updated roommates data
            with open(roommates_file, 'w') as f:
                json.dump(roommates, f, indent=2)
            
            return {
                "success": True, 
                "message": f"Successfully linked {roommate['name']} to Google account {user_info['email']}",
                "roommate_name": roommate['name'],
                "user_email": user_info['email']
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to link accounts: {str(e)}"}
    
    def unlink_roommate_from_google_account(self, roommate_id: int) -> Dict:
        """
        Unlink a roommate from their Google account.
        """
        try:
            # Load roommates data
            roommates_file = self.data_dir / "roommates.json"
            if not roommates_file.exists():
                return {"success": False, "error": "Roommates data not found"}
            
            with open(roommates_file, 'r') as f:
                roommates = json.load(f)
            
            # Find and unlink the roommate
            roommate_found = False
            for roommate in roommates:
                if roommate['id'] == roommate_id:
                    if not roommate.get('google_id'):
                        return {"success": False, "error": "Roommate is not linked to a Google account"}
                    
                    # Clear Google account information
                    roommate['google_id'] = None
                    roommate['google_profile_picture_url'] = None
                    roommate['linked_at'] = None
                    roommate_found = True
                    break
            
            if not roommate_found:
                return {"success": False, "error": f"Roommate with ID {roommate_id} not found"}
            
            # Save updated roommates data
            with open(roommates_file, 'w') as f:
                json.dump(roommates, f, indent=2)
            
            return {
                "success": True, 
                "message": f"Successfully unlinked {roommate['name']} from Google account"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to unlink account: {str(e)}"}
    
    def get_household_auth_status(self) -> Dict:
        """
        Get comprehensive authentication status for the entire household.
        Useful for admin dashboard and troubleshooting.
        """
        try:
            linked_roommates = self.get_linked_roommates()
            all_users = self.get_all_users()
            
            # Calculate statistics
            total_roommates = len(linked_roommates)
            authenticated_count = len([r for r in linked_roommates if r['auth_valid']])
            calendar_access_count = len([r for r in linked_roommates if r['calendar_access']])
            
            # Find users who are authenticated but not linked to roommates
            linked_google_ids = {r['google_id'] for r in linked_roommates}
            unlinked_users = [u for u in all_users if u['google_id'] not in linked_google_ids]
            
            return {
                "household_summary": {
                    "total_roommates": total_roommates,
                    "authenticated_roommates": authenticated_count,
                    "calendar_enabled_roommates": calendar_access_count,
                    "coverage_percentage": (calendar_access_count / total_roommates * 100) if total_roommates > 0 else 0
                },
                "linked_roommates": linked_roommates,
                "unlinked_authenticated_users": unlinked_users,
                "service_status": {
                    "api_available": self.is_available,
                    "credentials_configured": self.is_configured(),
                    "tokens_file_exists": self.auth_tokens_file.exists()
                },
                "recommendations": self._get_auth_recommendations(linked_roommates, unlinked_users)
            }
            
        except Exception as e:
            return {"error": f"Failed to get household auth status: {str(e)}"}
    
    def _get_auth_recommendations(self, linked_roommates: List[Dict], unlinked_users: List[Dict]) -> List[str]:
        """Generate recommendations for improving household authentication coverage."""
        recommendations = []
        
        # Check for roommates without authentication
        unauthenticated = [r for r in linked_roommates if not r['auth_valid']]
        if unauthenticated:
            recommendations.append(
                f"{len(unauthenticated)} roommate(s) need to re-authenticate: " +
                ", ".join([r['roommate_name'] for r in unauthenticated])
            )
        
        # Check for authentication without calendar access
        no_calendar = [r for r in linked_roommates if r['auth_valid'] and not r['calendar_access']]
        if no_calendar:
            recommendations.append(
                f"{len(no_calendar)} roommate(s) need calendar permissions: " +
                ", ".join([r['roommate_name'] for r in no_calendar])
            )
        
        # Check for unlinked authenticated users
        if unlinked_users:
            recommendations.append(
                f"{len(unlinked_users)} authenticated user(s) not linked to roommates: " +
                ", ".join([u['email'] for u in unlinked_users])
            )
        
        # Check for missing scopes
        missing_scopes_users = [r for r in linked_roommates if r.get('missing_scopes')]
        if missing_scopes_users:
            recommendations.append(
                f"{len(missing_scopes_users)} user(s) have incomplete permissions and need to re-authorize"
            )
        
        if not recommendations:
            recommendations.append("All roommates are properly authenticated with calendar access!")
        
        return recommendations
    
    def bulk_validate_calendar_access(self, google_ids: List[str]) -> Dict:
        """
        Validate calendar access for multiple users efficiently.
        Useful for checking status of all household members at once.
        """
        results = {
            "total_checked": len(google_ids),
            "valid_count": 0,
            "invalid_count": 0,
            "details": {}
        }
        
        for google_id in google_ids:
            validation_result = self.validate_calendar_access(google_id)
            results["details"][google_id] = validation_result
            
            if validation_result.get("valid", False):
                results["valid_count"] += 1
            else:
                results["invalid_count"] += 1
        
        return results
    
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