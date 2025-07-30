import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

class CalendarService:
    """Google Calendar integration service for RoomieRoster."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.credentials_file = self.data_dir / "google_credentials.json"
        self.token_file = self.data_dir / "google_token.json"
        self.calendar_config_file = self.data_dir / "calendar_config.json"
        self.service = None
        self.is_available = GOOGLE_AVAILABLE
        
        if not self.is_available:
            print("Google Calendar API dependencies not available. Install with: pip install -r requirements.txt")
    
    def _get_default_redirect_uri(self) -> str:
        """Get the appropriate calendar redirect URI based on environment."""
        # Check for custom base URL override first (useful for other deployment platforms)
        base_url = os.getenv('APP_BASE_URL')
        if base_url:
            return f'{base_url.rstrip("/")}/api/calendar/callback'
        
        # Check if we're running on Render - use explicit production URL
        # Render sets PORT environment variable, and we can also check for RENDER_SERVICE_NAME
        if os.getenv('RENDER_SERVICE_NAME') or (os.getenv('PORT') and not os.getenv('FLASK_ENV') == 'development'):
            # Production environment - use the known production URL
            return 'https://roomie-roster.onrender.com/api/calendar/callback'
        
        # Development environment - detect the actual port being used
        port = os.getenv('PORT') or os.getenv('FLASK_RUN_PORT', '5000')
        
        # Handle common development port scenarios (5000, 5001, 5002)
        if port in ['5000', '5001', '5002']:
            return f'http://localhost:{port}/api/calendar/callback'
        
        # Default fallback for development
        return 'http://localhost:5000/api/calendar/callback'
    
    def is_configured(self) -> bool:
        """Check if Google Calendar is properly configured."""
        if not self.is_available:
            return False
        return self.credentials_file.exists() and self._has_valid_token()
    
    def _has_valid_token(self) -> bool:
        """Check if we have a valid token file."""
        if not self.token_file.exists():
            return False
        
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.SCOPES)
            return creds.valid or creds.refresh_token is not None
        except Exception:
            return False
    
    def setup_credentials(self, credentials_json: Dict) -> Dict:
        """Set up Google Calendar credentials from JSON data."""
        if not self.is_available:
            raise Exception("Google Calendar API dependencies not installed")
        
        try:
            # Save credentials to file
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials_json, f, indent=2)
            
            return {"message": "Credentials saved successfully. Please complete OAuth flow."}
        except Exception as e:
            raise Exception(f"Failed to save credentials: {str(e)}")
    
    def get_oauth_url(self) -> str:
        """Get OAuth authorization URL."""
        if not self.is_available:
            raise Exception("Google Calendar API dependencies not installed")
        
        if not self.credentials_file.exists():
            raise Exception("Credentials file not found. Please upload credentials first.")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), self.SCOPES
            )
            flow.redirect_uri = self._get_default_redirect_uri()
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            return auth_url
        except Exception as e:
            raise Exception(f"Failed to generate OAuth URL: {str(e)}")
    
    def handle_oauth_callback(self, authorization_code: str) -> Dict:
        """Handle OAuth callback and save token."""
        if not self.is_available:
            raise Exception("Google Calendar API dependencies not installed")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), self.SCOPES
            )
            flow.redirect_uri = self._get_default_redirect_uri()
            
            flow.fetch_token(code=authorization_code)
            
            # Save token
            with open(self.token_file, 'w') as f:
                f.write(flow.credentials.to_json())
            
            return {"message": "OAuth setup completed successfully"}
        except Exception as e:
            raise Exception(f"OAuth callback failed: {str(e)}")
    
    def _get_service(self):
        """Get authenticated Google Calendar service."""
        if not self.is_available:
            raise Exception("Google Calendar API dependencies not installed")
        
        if self.service:
            return self.service
        
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.SCOPES)
        
        # If there are no valid credentials, raise exception
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open(self.token_file, 'w') as f:
                        f.write(creds.to_json())
                except Exception as e:
                    raise Exception(f"Failed to refresh token: {str(e)}")
            else:
                raise Exception("No valid credentials found. Please complete OAuth setup.")
        
        self.service = build('calendar', 'v3', credentials=creds)
        return self.service
    
    def get_calendar_list(self) -> List[Dict]:
        """Get list of user's calendars."""
        try:
            service = self._get_service()
            calendars_result = service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            return [{
                'id': cal['id'],
                'name': cal['summary'],
                'primary': cal.get('primary', False),
                'access_role': cal.get('accessRole', 'reader')
            } for cal in calendars]
        except Exception as e:
            raise Exception(f"Failed to get calendars: {str(e)}")
    
    def create_event(self, calendar_id: str, event_data: Dict) -> Dict:
        """Create a calendar event."""
        try:
            service = self._get_service()
            
            event = {
                'summary': event_data['title'],
                'description': event_data.get('description', ''),
                'start': {
                    'dateTime': event_data['start_time'],
                    'timeZone': 'America/Los_Angeles',  # Default timezone
                },
                'end': {
                    'dateTime': event_data['end_time'],
                    'timeZone': 'America/Los_Angeles',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            if 'location' in event_data:
                event['location'] = event_data['location']
            
            result = service.events().insert(calendarId=calendar_id, body=event).execute()
            
            return {
                'id': result['id'],
                'htmlLink': result['htmlLink'],
                'summary': result['summary']
            }
        except Exception as e:
            raise Exception(f"Failed to create event: {str(e)}")
    
    def delete_event(self, calendar_id: str, event_id: str) -> Dict:
        """Delete a calendar event."""
        try:
            service = self._get_service()
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            
            return {"message": "Event deleted successfully"}
        except Exception as e:
            raise Exception(f"Failed to delete event: {str(e)}")
    
    def get_calendar_config(self) -> Dict:
        """Get calendar integration configuration."""
        try:
            if self.calendar_config_file.exists():
                with open(self.calendar_config_file, 'r') as f:
                    return json.load(f)
            else:
                return {
                    "enabled": False,
                    "default_calendar_id": None,
                    "reminder_settings": {
                        "laundry_reminders": True,
                        "chore_reminders": False,
                        "reminder_minutes": [30, 10]
                    }
                }
        except Exception as e:
            raise Exception(f"Failed to get calendar config: {str(e)}")
    
    def save_calendar_config(self, config: Dict) -> Dict:
        """Save calendar integration configuration."""
        try:
            with open(self.calendar_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return {"message": "Calendar configuration saved successfully"}
        except Exception as e:
            raise Exception(f"Failed to save calendar config: {str(e)}")
    
    def create_laundry_reminder(self, laundry_slot: Dict) -> Optional[Dict]:
        """Create a calendar event for a laundry slot."""
        config = self.get_calendar_config()
        
        if not config.get("enabled") or not config.get("reminder_settings", {}).get("laundry_reminders"):
            return None
        
        calendar_id = config.get("default_calendar_id")
        if not calendar_id:
            return None
        
        try:
            # Parse the time slot
            date = laundry_slot['date']
            time_range = laundry_slot['time_slot']
            start_time, end_time = time_range.split('-')
            
            # Create datetime objects
            start_datetime = f"{date}T{start_time}:00"
            end_datetime = f"{date}T{end_time}:00"
            
            event_data = {
                'title': f"🧺 Laundry - {laundry_slot['load_type'].title()}",
                'description': f"Laundry scheduled for {laundry_slot['roommate_name']}\n" +
                              f"Load type: {laundry_slot['load_type']}\n" +
                              f"Machine: {laundry_slot['machine_type']}\n" +
                              f"Estimated loads: {laundry_slot['estimated_loads']}\n" +
                              (f"Notes: {laundry_slot['notes']}" if laundry_slot.get('notes') else ""),
                'start_time': start_datetime,
                'end_time': end_datetime,
                'location': 'Laundry Room'
            }
            
            result = self.create_event(calendar_id, event_data)
            return result
        except Exception as e:
            print(f"Failed to create laundry reminder: {str(e)}")
            return None
    
    def get_status(self) -> Dict:
        """Get calendar service status."""
        return {
            "google_api_available": self.is_available,
            "credentials_configured": self.credentials_file.exists(),
            "oauth_completed": self._has_valid_token(),
            "fully_configured": self.is_configured(),
            "config_exists": self.calendar_config_file.exists()
        }