import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class CalendarPreferencesService:
    """
    Service for managing household calendar notification preferences.
    Handles user-specific settings for calendar sync and notifications.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.preferences_file = self.data_dir / "household_calendar_preferences.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize preferences file if it doesn't exist
        if not self.preferences_file.exists():
            self._initialize_preferences_file()
    
    def _initialize_preferences_file(self):
        """Initialize the preferences file with default structure."""
        initial_data = {
            "household_defaults": self._get_default_household_preferences(),
            "user_preferences": {},
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.preferences_file, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def _get_default_household_preferences(self) -> Dict:
        """Get default household-wide preferences."""
        return {
            "chore_notifications": {
                "enabled": True,
                "notify_assignee": True,
                "notify_household": True,
                "reminder_minutes": [30, 10],  # Remind 30 min and 10 min before due
                "include_sub_chores": True,
                "event_duration_minutes": 60  # Default chore event duration
            },
            "laundry_notifications": {
                "enabled": True,
                "block_all_calendars": True,
                "reminder_minutes": [15],  # Remind 15 min before laundry starts
                "include_buffer_time": True,
                "buffer_minutes": 15  # Extra time for setup/cleanup
            },
            "notification_types": {
                "assignment_notifications": True,  # New assignments
                "due_date_reminders": True,       # Due date approaching
                "completion_updates": False,      # When chores are completed
                "overdue_alerts": True           # When chores are overdue
            },
            "event_appearance": {
                "chore_emoji": "🧹",
                "laundry_emoji": "🧺",
                "blocking_emoji": "🚫",
                "include_points": True,
                "include_roommate_names": True,
                "color_coding": True
            }
        }
    
    def _get_default_user_preferences(self) -> Dict:
        """Get default user-specific preferences."""
        return {
            "calendar_sync": {
                "enabled": False,
                "selected_calendar_id": "primary",
                "auto_sync": True
            },
            "notification_overrides": {
                "chore_notifications": None,      # None means use household default
                "laundry_notifications": None,
                "reminder_minutes": None,
                "event_duration_minutes": None
            },
            "personal_preferences": {
                "all_day_events": False,
                "timezone": "America/Los_Angeles",
                "event_privacy": "default",       # default, public, private
                "include_description": True
            },
            "opt_out_settings": {
                "chore_assignments": False,       # Opt out of chore assignment notifications
                "laundry_blocking": False,        # Opt out of laundry time blocking
                "household_reminders": False,     # Opt out of household-wide reminders
                "completion_notifications": True  # Opt out of completion notifications
            },
            "advanced_settings": {
                "batch_sync": True,              # Allow batching of calendar operations
                "retry_failed_syncs": True,      # Retry failed calendar syncs
                "max_sync_attempts": 3,
                "sync_delay_seconds": 0          # Delay before syncing (for batching)
            },
            "last_updated": datetime.now().isoformat(),
            "preferences_version": "1.0"
        }
    
    def get_household_preferences(self) -> Dict:
        """Get household-wide default preferences."""
        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
            return data.get("household_defaults", self._get_default_household_preferences())
        except Exception as e:
            print(f"Error loading household preferences: {str(e)}")
            return self._get_default_household_preferences()
    
    def update_household_preferences(self, preferences: Dict) -> Dict:
        """Update household-wide default preferences."""
        try:
            # Load existing data
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
            
            # Update household defaults
            current_defaults = data.get("household_defaults", self._get_default_household_preferences())
            
            # Deep merge the preferences
            updated_defaults = self._deep_merge(current_defaults, preferences)
            
            data["household_defaults"] = updated_defaults
            data["last_updated"] = datetime.now().isoformat()
            
            # Save back to file
            with open(self.preferences_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {"success": True, "message": "Household preferences updated successfully"}
        except Exception as e:
            return {"success": False, "error": f"Failed to update household preferences: {str(e)}"}
    
    def get_user_preferences(self, google_id: str) -> Dict:
        """Get preferences for a specific user."""
        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
            
            user_prefs = data.get("user_preferences", {}).get(google_id)
            
            if not user_prefs:
                # Return default preferences for new user
                return self._get_default_user_preferences()
            
            # Merge with defaults to ensure all fields are present
            default_prefs = self._get_default_user_preferences()
            return self._deep_merge(default_prefs, user_prefs)
            
        except Exception as e:
            print(f"Error loading user preferences for {google_id}: {str(e)}")
            return self._get_default_user_preferences()
    
    def update_user_preferences(self, google_id: str, preferences: Dict) -> Dict:
        """Update preferences for a specific user."""
        try:
            # Load existing data
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
            
            # Ensure user_preferences section exists
            if "user_preferences" not in data:
                data["user_preferences"] = {}
            
            # Get current user preferences or defaults
            current_prefs = data["user_preferences"].get(google_id, self._get_default_user_preferences())
            
            # Deep merge with new preferences
            updated_prefs = self._deep_merge(current_prefs, preferences)
            updated_prefs["last_updated"] = datetime.now().isoformat()
            
            # Save updated preferences
            data["user_preferences"][google_id] = updated_prefs
            data["last_updated"] = datetime.now().isoformat()
            
            # Save back to file
            with open(self.preferences_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {"success": True, "message": "User preferences updated successfully"}
        except Exception as e:
            return {"success": False, "error": f"Failed to update user preferences: {str(e)}"}
    
    def get_effective_preferences(self, google_id: str) -> Dict:
        """
        Get effective preferences for a user, combining household defaults with user overrides.
        """
        household_prefs = self.get_household_preferences()
        user_prefs = self.get_user_preferences(google_id)
        
        # Start with household defaults
        effective_prefs = household_prefs.copy()
        
        # Apply user overrides where specified
        overrides = user_prefs.get("notification_overrides", {})
        
        for key, value in overrides.items():
            if value is not None:  # User has specified an override
                if key in effective_prefs:
                    effective_prefs[key] = value
        
        # Add user-specific settings
        effective_prefs["user_settings"] = {
            "calendar_sync": user_prefs.get("calendar_sync", {}),
            "personal_preferences": user_prefs.get("personal_preferences", {}),
            "opt_out_settings": user_prefs.get("opt_out_settings", {}),
            "advanced_settings": user_prefs.get("advanced_settings", {})
        }
        
        return effective_prefs
    
    def should_send_notification(self, google_id: str, notification_type: str, event_category: str = "chore") -> bool:
        """
        Determine if a notification should be sent to a specific user.
        
        Args:
            google_id: User's Google ID
            notification_type: Type of notification (assignment, reminder, completion, etc.)
            event_category: Category of event (chore, laundry, etc.)
        """
        try:
            effective_prefs = self.get_effective_preferences(google_id)
            user_settings = effective_prefs.get("user_settings", {})
            
            # Check if calendar sync is enabled
            if not user_settings.get("calendar_sync", {}).get("enabled", False):
                return False
            
            # Check opt-out settings
            opt_out_settings = user_settings.get("opt_out_settings", {})
            
            if event_category == "chore":
                if notification_type == "assignment" and opt_out_settings.get("chore_assignments", False):
                    return False
                if notification_type == "reminder" and opt_out_settings.get("household_reminders", False):
                    return False
                if notification_type == "completion" and opt_out_settings.get("completion_notifications", False):
                    return False
            
            elif event_category == "laundry":
                if notification_type == "blocking" and opt_out_settings.get("laundry_blocking", False):
                    return False
                if notification_type == "reminder" and opt_out_settings.get("household_reminders", False):
                    return False
            
            # Check category-specific settings
            if event_category == "chore":
                return effective_prefs.get("chore_notifications", {}).get("enabled", True)
            elif event_category == "laundry":
                return effective_prefs.get("laundry_notifications", {}).get("enabled", True)
            
            return True
            
        except Exception as e:
            print(f"Error checking notification permissions for {google_id}: {str(e)}")
            return False  # Fail safe - don't send notification if unsure
    
    def get_user_calendar_config(self, google_id: str) -> Dict:
        """Get calendar configuration for a specific user."""
        user_prefs = self.get_user_preferences(google_id)
        calendar_sync = user_prefs.get("calendar_sync", {})
        personal_prefs = user_prefs.get("personal_preferences", {})
        
        return {
            "enabled": calendar_sync.get("enabled", False),
            "selected_calendar_id": calendar_sync.get("selected_calendar_id", "primary"),
            "auto_sync": calendar_sync.get("auto_sync", True),
            "all_day_events": personal_prefs.get("all_day_events", False),
            "timezone": personal_prefs.get("timezone", "America/Los_Angeles"),
            "event_privacy": personal_prefs.get("event_privacy", "default"),
            "include_description": personal_prefs.get("include_description", True)
        }
    
    def get_all_users_with_sync_enabled(self) -> List[str]:
        """Get list of Google IDs for all users with calendar sync enabled."""
        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
            
            user_preferences = data.get("user_preferences", {})
            enabled_users = []
            
            for google_id, prefs in user_preferences.items():
                if prefs.get("calendar_sync", {}).get("enabled", False):
                    enabled_users.append(google_id)
            
            return enabled_users
        except Exception as e:
            print(f"Error getting users with sync enabled: {str(e)}")
            return []
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def export_user_preferences(self, google_id: str) -> Dict:
        """Export user preferences for backup or transfer."""
        return {
            "google_id": google_id,
            "preferences": self.get_user_preferences(google_id),
            "effective_preferences": self.get_effective_preferences(google_id),
            "exported_at": datetime.now().isoformat()
        }
    
    def import_user_preferences(self, google_id: str, preferences_data: Dict) -> Dict:
        """Import user preferences from backup or transfer."""
        try:
            if "preferences" not in preferences_data:
                return {"success": False, "error": "Invalid preferences data format"}
            
            return self.update_user_preferences(google_id, preferences_data["preferences"])
        except Exception as e:
            return {"success": False, "error": f"Failed to import preferences: {str(e)}"}
    
    def reset_user_preferences(self, google_id: str) -> Dict:
        """Reset user preferences to defaults."""
        try:
            # Load existing data
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
            
            # Remove user preferences (will fall back to defaults)
            if "user_preferences" in data and google_id in data["user_preferences"]:
                del data["user_preferences"][google_id]
                data["last_updated"] = datetime.now().isoformat()
                
                # Save back to file
                with open(self.preferences_file, 'w') as f:
                    json.dump(data, f, indent=2)
            
            return {"success": True, "message": "User preferences reset to defaults"}
        except Exception as e:
            return {"success": False, "error": f"Failed to reset preferences: {str(e)}"}
    
    def get_preferences_summary(self) -> Dict:
        """Get a summary of all preferences for admin/debugging purposes."""
        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
            
            user_preferences = data.get("user_preferences", {})
            
            summary = {
                "household_defaults": data.get("household_defaults", {}),
                "total_users": len(user_preferences),
                "users_with_sync_enabled": len(self.get_all_users_with_sync_enabled()),
                "file_info": {
                    "created_at": data.get("created_at"),
                    "last_updated": data.get("last_updated"),
                    "file_size_bytes": self.preferences_file.stat().st_size if self.preferences_file.exists() else 0
                },
                "user_summary": {}
            }
            
            # Add summary for each user
            for google_id, prefs in user_preferences.items():
                summary["user_summary"][google_id] = {
                    "sync_enabled": prefs.get("calendar_sync", {}).get("enabled", False),
                    "selected_calendar": prefs.get("calendar_sync", {}).get("selected_calendar_id", "primary"),
                    "last_updated": prefs.get("last_updated"),
                    "has_overrides": bool(prefs.get("notification_overrides", {})),
                    "opt_out_count": len([k for k, v in prefs.get("opt_out_settings", {}).items() if v])
                }
            
            return summary
        except Exception as e:
            return {"error": f"Failed to generate preferences summary: {str(e)}"}