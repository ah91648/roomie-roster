import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    Credentials = None

class UserCalendarService:
    """User-specific Google Calendar integration for RoomieRoster chore assignments."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.user_calendar_configs_file = self.data_dir / "user_calendar_configs.json"
        self.is_available = GOOGLE_AVAILABLE
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        if not self.is_available:
            print("Google Calendar API dependencies not available for user calendar service.")
    
    def get_user_calendar_config(self, google_id: str) -> Dict:
        """Get calendar configuration for a specific user."""
        try:
            if not self.user_calendar_configs_file.exists():
                return self._get_default_config()
            
            with open(self.user_calendar_configs_file, 'r') as f:
                all_configs = json.load(f)
            
            return all_configs.get(google_id, self._get_default_config())
        except Exception as e:
            print(f"Failed to get user calendar config: {str(e)}")
            return self._get_default_config()
    
    def save_user_calendar_config(self, google_id: str, config: Dict) -> Dict:
        """Save calendar configuration for a specific user."""
        try:
            # Load existing configs
            all_configs = {}
            if self.user_calendar_configs_file.exists():
                with open(self.user_calendar_configs_file, 'r') as f:
                    all_configs = json.load(f)
            
            # Update user's config
            all_configs[google_id] = {
                **self._get_default_config(),
                **config,
                'last_updated': datetime.now().isoformat()
            }
            
            # Save back to file
            with open(self.user_calendar_configs_file, 'w') as f:
                json.dump(all_configs, f, indent=2)
            
            return {"message": "User calendar configuration saved successfully"}
        except Exception as e:
            raise Exception(f"Failed to save user calendar config: {str(e)}")
    
    def _get_default_config(self) -> Dict:
        """Get default calendar configuration."""
        return {
            "chore_sync_enabled": False,
            "selected_calendar_id": "primary",
            "reminder_settings": {
                "chore_reminders": True,
                "reminder_minutes": [30, 10],
                "all_day_events": False
            },
            "sync_preferences": {
                "sync_assigned_chores": True,
                "sync_completed_chores": False,
                "auto_sync": True,
                "include_sub_chores": True
            },
            "event_settings": {
                "event_prefix": "🧹",
                "include_points": True,
                "include_frequency": True,
                "include_notes": True
            }
        }
    
    def get_user_credentials(self, google_id: str) -> Optional[Credentials]:
        """Get Google Calendar credentials for a specific user."""
        try:
            # Load auth tokens to get user's credentials
            auth_tokens_file = self.data_dir / "google_auth_tokens.json"
            if not auth_tokens_file.exists():
                return None
            
            with open(auth_tokens_file, 'r') as f:
                auth_tokens = json.load(f)
            
            user_data = auth_tokens.get(google_id)
            if not user_data:
                return None
            
            # Parse credentials
            creds_data = json.loads(user_data['credentials'])
            creds = Credentials.from_authorized_user_info(creds_data, self.SCOPES)
            
            # Refresh if needed
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                
                # Update stored credentials
                user_data['credentials'] = creds.to_json()
                auth_tokens[google_id] = user_data
                with open(auth_tokens_file, 'w') as f:
                    json.dump(auth_tokens, f, indent=2)
            
            return creds
        except Exception as e:
            print(f"Failed to get user credentials for {google_id}: {str(e)}")
            return None
    
    def get_user_calendars(self, google_id: str) -> List[Dict]:
        """Get list of calendars for a specific user."""
        if not self.is_available:
            raise Exception("Google Calendar API not available")
        
        try:
            creds = self.get_user_credentials(google_id)
            if not creds:
                raise Exception("No valid credentials found for user")
            
            service = build('calendar', 'v3', credentials=creds)
            calendars_result = service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            return [{
                'id': cal['id'],
                'name': cal['summary'],
                'primary': cal.get('primary', False),
                'access_role': cal.get('accessRole', 'reader'),
                'color': cal.get('backgroundColor', '#4285f4')
            } for cal in calendars if cal.get('accessRole') in ['owner', 'writer']]
        except Exception as e:
            raise Exception(f"Failed to get user calendars: {str(e)}")
    
    def sync_chore_to_calendar(self, google_id: str, assignment: Dict) -> Optional[Dict]:
        """Sync a chore assignment to user's Google Calendar."""
        if not self.is_available:
            return None
        
        try:
            config = self.get_user_calendar_config(google_id)
            if not config.get('chore_sync_enabled'):
                return None
            
            creds = self.get_user_credentials(google_id)
            if not creds:
                return None
            
            service = build('calendar', 'v3', credentials=creds)
            calendar_id = config.get('selected_calendar_id', 'primary')
            
            # Build event data
            event_data = self._build_chore_event(assignment, config)
            
            # Create the event
            result = service.events().insert(calendarId=calendar_id, body=event_data).execute()
            
            return {
                'event_id': result['id'],
                'event_link': result['htmlLink'],
                'calendar_id': calendar_id,
                'title': result['summary']
            }
        except Exception as e:
            print(f"Failed to sync chore to calendar for user {google_id}: {str(e)}")
            return None
    
    def update_chore_in_calendar(self, google_id: str, assignment: Dict, event_id: str) -> Optional[Dict]:
        """Update an existing chore event in user's calendar."""
        if not self.is_available:
            return None
        
        try:
            config = self.get_user_calendar_config(google_id)
            if not config.get('chore_sync_enabled'):
                return None
            
            creds = self.get_user_credentials(google_id)
            if not creds:
                return None
            
            service = build('calendar', 'v3', credentials=creds)
            calendar_id = config.get('selected_calendar_id', 'primary')
            
            # Build updated event data
            event_data = self._build_chore_event(assignment, config)
            
            # Update the event
            result = service.events().update(
                calendarId=calendar_id, 
                eventId=event_id, 
                body=event_data
            ).execute()
            
            return {
                'event_id': result['id'],
                'event_link': result['htmlLink'],
                'calendar_id': calendar_id,
                'title': result['summary']
            }
        except Exception as e:
            print(f"Failed to update chore in calendar for user {google_id}: {str(e)}")
            return None
    
    def delete_chore_from_calendar(self, google_id: str, event_id: str) -> bool:
        """Delete a chore event from user's calendar."""
        if not self.is_available:
            return False
        
        try:
            config = self.get_user_calendar_config(google_id)
            creds = self.get_user_credentials(google_id)
            if not creds:
                return False
            
            service = build('calendar', 'v3', credentials=creds)
            calendar_id = config.get('selected_calendar_id', 'primary')
            
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return True
        except Exception as e:
            print(f"Failed to delete chore from calendar for user {google_id}: {str(e)}")
            return False
    
    def sync_all_user_chores(self, google_id: str, assignments: List[Dict]) -> Dict:
        """Sync all of a user's chore assignments to their calendar."""
        if not self.is_available:
            return {"synced": 0, "errors": ["Google Calendar API not available"]}
        
        config = self.get_user_calendar_config(google_id)
        if not config.get('chore_sync_enabled'):
            return {"synced": 0, "errors": ["Calendar sync disabled for user"]}
        
        synced_count = 0
        errors = []
        synced_events = []
        
        for assignment in assignments:
            try:
                result = self.sync_chore_to_calendar(google_id, assignment)
                if result:
                    synced_count += 1
                    synced_events.append({
                        'chore_id': assignment['chore_id'],
                        'event_id': result['event_id'],
                        'event_link': result['event_link']
                    })
                else:
                    errors.append(f"Failed to sync chore: {assignment['chore_name']}")
            except Exception as e:
                errors.append(f"Error syncing {assignment['chore_name']}: {str(e)}")
        
        return {
            "synced": synced_count,
            "errors": errors,
            "events": synced_events
        }
    
    def _build_chore_event(self, assignment: Dict, config: Dict) -> Dict:
        """Build Google Calendar event data from chore assignment."""
        event_settings = config.get('event_settings', {})
        reminder_settings = config.get('reminder_settings', {})
        
        # Build title
        prefix = event_settings.get('event_prefix', '🧹')
        title = f"{prefix} {assignment['chore_name']}"
        
        if event_settings.get('include_points', True):
            title += f" ({assignment['points']} pts)"
        
        # Build description
        description_parts = [
            f"Chore: {assignment['chore_name']}",
            f"Assigned to: {assignment['roommate_name']}",
            f"Points: {assignment['points']}"
        ]
        
        if event_settings.get('include_frequency', True):
            description_parts.append(f"Frequency: {assignment['frequency']}")
        
        if assignment.get('type'):
            description_parts.append(f"Type: {assignment['type']}")
        
        description_parts.append(f"Assigned: {assignment['assigned_date']}")
        description_parts.append("\n📱 Created by RoomieRoster")
        
        # Parse due date
        due_date = datetime.fromisoformat(assignment['due_date'].replace('Z', '+00:00'))
        
        # Create event structure
        event = {
            'summary': title,
            'description': '\n'.join(description_parts),
            'start': {},
            'end': {},
            'reminders': {
                'useDefault': False,
                'overrides': []
            }
        }
        
        # Set time (all-day vs timed event)
        if reminder_settings.get('all_day_events', False):
            event['start']['date'] = due_date.strftime('%Y-%m-%d')
            event['end']['date'] = (due_date + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            # Default to 1-hour event ending at due time
            event['start']['dateTime'] = (due_date - timedelta(hours=1)).isoformat()
            event['end']['dateTime'] = due_date.isoformat()
            event['start']['timeZone'] = 'America/Los_Angeles'
            event['end']['timeZone'] = 'America/Los_Angeles'
        
        # Add reminders
        if reminder_settings.get('chore_reminders', True):
            for minutes in reminder_settings.get('reminder_minutes', [30, 10]):
                event['reminders']['overrides'].append({
                    'method': 'popup',
                    'minutes': minutes
                })
        
        return event
    
    def get_sync_status(self, google_id: str) -> Dict:
        """Get calendar sync status for a user."""
        config = self.get_user_calendar_config(google_id)
        has_credentials = self.get_user_credentials(google_id) is not None
        
        return {
            "sync_enabled": config.get('chore_sync_enabled', False),
            "has_credentials": has_credentials,
            "selected_calendar": config.get('selected_calendar_id', 'primary'),
            "auto_sync": config.get('sync_preferences', {}).get('auto_sync', True),
            "last_updated": config.get('last_updated'),
            "api_available": self.is_available
        }