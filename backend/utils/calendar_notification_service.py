import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from enum import Enum

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from .household_calendar_service import HouseholdCalendarService
from .calendar_preferences_service import CalendarPreferencesService
from .auth_service import AuthService

class NotificationType(Enum):
    """Types of calendar notifications."""
    CHORE_ASSIGNMENT = "chore_assignment"
    CHORE_REMINDER = "chore_reminder"
    CHORE_OVERDUE = "chore_overdue"
    LAUNDRY_BLOCKING = "laundry_blocking"
    LAUNDRY_REMINDER = "laundry_reminder"
    COMPLETION_UPDATE = "completion_update"

class CalendarNotificationService:
    """
    High-level service for managing calendar notifications across the household.
    Orchestrates event creation, distribution, and lifecycle management.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        
        # Initialize underlying services
        self.household_calendar = HouseholdCalendarService(data_dir)
        self.preferences = CalendarPreferencesService(data_dir)
        self.auth_service = AuthService(data_dir)
        
        # Event tracking file for managing event lifecycle
        self.event_tracking_file = self.data_dir / "calendar_event_tracking.json"
        
        self.is_available = GOOGLE_AVAILABLE
        
        # Ensure tracking file exists
        if not self.event_tracking_file.exists():
            self._initialize_event_tracking()
        
        if not self.is_available:
            print("Google Calendar API dependencies not available for calendar notification service.")
    
    def _initialize_event_tracking(self):
        """Initialize the event tracking file."""
        initial_data = {
            "chore_events": {},           # Maps chore assignment IDs to event details
            "laundry_events": {},         # Maps laundry slot IDs to event details
            "household_events": {},       # Maps generic event IDs to event details
            "event_metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_events_created": 0,
                "total_events_deleted": 0
            }
        }
        
        with open(self.event_tracking_file, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def _load_event_tracking(self) -> Dict:
        """Load event tracking data."""
        try:
            with open(self.event_tracking_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading event tracking: {str(e)}")
            self._initialize_event_tracking()
            with open(self.event_tracking_file, 'r') as f:
                return json.load(f)
    
    def _save_event_tracking(self, data: Dict):
        """Save event tracking data."""
        try:
            data["event_metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.event_tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving event tracking: {str(e)}")
    
    def create_chore_assignment_notification(
        self, 
        assignment: Dict,
        notification_type: NotificationType = NotificationType.CHORE_ASSIGNMENT
    ) -> Dict:
        """
        Create calendar notifications for a chore assignment.
        
        Args:
            assignment: Chore assignment data
            notification_type: Type of notification being created
        
        Returns:
            Dict with creation results and tracking information
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        try:
            # Get assignee information
            assignee_google_id = self._get_roommate_google_id(assignment['roommate_id'])
            
            # Get household preferences for event formatting
            household_prefs = self.preferences.get_household_preferences()
            
            # Create base event data
            event_data = self._build_chore_event_data(assignment, household_prefs, notification_type)
            
            # Determine who should receive this notification
            target_recipients = self._get_notification_recipients(
                notification_type=notification_type,
                assignee_google_id=assignee_google_id,
                event_category="chore"
            )
            
            if not target_recipients:
                return {"success": False, "error": "No recipients found for chore notification"}
            
            # Create customized events for each recipient
            results = {
                "success": True,
                "assignment_id": f"{assignment['chore_id']}_{assignment['roommate_id']}_{assignment['assigned_date']}",
                "notification_type": notification_type.value,
                "total_recipients": len(target_recipients),
                "successful_notifications": 0,
                "failed_notifications": 0,
                "recipient_details": {}
            }
            
            event_tracking_data = self._load_event_tracking()
            assignment_key = results["assignment_id"]
            
            # Create events for each recipient
            for recipient in target_recipients:
                try:
                    # Customize event for this recipient
                    customized_event = self._customize_event_for_recipient(
                        event_data, 
                        recipient, 
                        assignee_google_id,
                        assignment
                    )
                    
                    # Create the calendar event
                    event_result = self.household_calendar.user_calendar_service.sync_chore_to_calendar(
                        recipient['google_id'], 
                        customized_event
                    )
                    
                    if event_result:
                        results["successful_notifications"] += 1
                        results["recipient_details"][recipient['google_id']] = {
                            "success": True,
                            "roommate_name": recipient['roommate_name'],
                            "event_id": event_result['event_id'],
                            "event_link": event_result['event_link'],
                            "calendar_id": event_result['calendar_id']
                        }
                        
                        # Track the event for future management
                        if assignment_key not in event_tracking_data["chore_events"]:
                            event_tracking_data["chore_events"][assignment_key] = {}
                        
                        event_tracking_data["chore_events"][assignment_key][recipient['google_id']] = {
                            "event_id": event_result['event_id'],
                            "calendar_id": event_result['calendar_id'],
                            "created_at": datetime.now().isoformat(),
                            "notification_type": notification_type.value,
                            "is_assignee": recipient['google_id'] == assignee_google_id
                        }
                    else:
                        results["failed_notifications"] += 1
                        results["recipient_details"][recipient['google_id']] = {
                            "success": False,
                            "roommate_name": recipient['roommate_name'],
                            "error": "Failed to create calendar event"
                        }
                        
                except Exception as e:
                    results["failed_notifications"] += 1
                    results["recipient_details"][recipient['google_id']] = {
                        "success": False,
                        "roommate_name": recipient.get('roommate_name', 'Unknown'),
                        "error": str(e)
                    }
            
            # Update tracking data
            event_tracking_data["event_metadata"]["total_events_created"] += results["successful_notifications"]
            self._save_event_tracking(event_tracking_data)
            
            # Update overall success status
            results["success"] = results["successful_notifications"] > 0
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Failed to create chore assignment notification: {str(e)}"}
    
    def create_laundry_blocking_notification(self, laundry_slot: Dict) -> Dict:
        """
        Create laundry time blocking events on all roommates' calendars.
        
        Args:
            laundry_slot: Laundry slot data
        
        Returns:
            Dict with creation results and tracking information
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        try:
            # Get household preferences
            household_prefs = self.preferences.get_household_preferences()
            
            # Create blocking event data
            blocking_event = self._build_laundry_blocking_event_data(laundry_slot, household_prefs)
            
            # Get recipients who want laundry blocking notifications
            target_recipients = self._get_notification_recipients(
                notification_type=NotificationType.LAUNDRY_BLOCKING,
                assignee_google_id=None,
                event_category="laundry"
            )
            
            if not target_recipients:
                return {"success": False, "error": "No recipients found for laundry blocking"}
            
            # Create the blocking events
            results = {
                "success": True,
                "laundry_slot_id": laundry_slot['id'],
                "notification_type": NotificationType.LAUNDRY_BLOCKING.value,
                "total_recipients": len(target_recipients),
                "successful_blocks": 0,
                "failed_blocks": 0,
                "recipient_details": {}
            }
            
            event_tracking_data = self._load_event_tracking()
            slot_key = str(laundry_slot['id'])
            
            # Create blocking events for each recipient
            for recipient in target_recipients:
                try:
                    # Customize blocking event for this recipient
                    customized_event = self._customize_blocking_event_for_recipient(
                        blocking_event,
                        recipient,
                        laundry_slot
                    )
                    
                    # Create the calendar event
                    event_result = self.household_calendar.user_calendar_service.sync_chore_to_calendar(
                        recipient['google_id'],
                        customized_event
                    )
                    
                    if event_result:
                        results["successful_blocks"] += 1
                        results["recipient_details"][recipient['google_id']] = {
                            "success": True,
                            "roommate_name": recipient['roommate_name'],
                            "event_id": event_result['event_id'],
                            "event_link": event_result['event_link'],
                            "calendar_id": event_result['calendar_id']
                        }
                        
                        # Track the event
                        if slot_key not in event_tracking_data["laundry_events"]:
                            event_tracking_data["laundry_events"][slot_key] = {}
                        
                        event_tracking_data["laundry_events"][slot_key][recipient['google_id']] = {
                            "event_id": event_result['event_id'],
                            "calendar_id": event_result['calendar_id'],
                            "created_at": datetime.now().isoformat(),
                            "notification_type": NotificationType.LAUNDRY_BLOCKING.value
                        }
                    else:
                        results["failed_blocks"] += 1
                        results["recipient_details"][recipient['google_id']] = {
                            "success": False,
                            "roommate_name": recipient['roommate_name'],
                            "error": "Failed to create blocking event"
                        }
                        
                except Exception as e:
                    results["failed_blocks"] += 1
                    results["recipient_details"][recipient['google_id']] = {
                        "success": False,
                        "roommate_name": recipient.get('roommate_name', 'Unknown'),
                        "error": str(e)
                    }
            
            # Update tracking data
            event_tracking_data["event_metadata"]["total_events_created"] += results["successful_blocks"]
            self._save_event_tracking(event_tracking_data)
            
            # Update overall success status
            results["success"] = results["successful_blocks"] > 0
            
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Failed to create laundry blocking notification: {str(e)}"}
    
    def delete_chore_events(self, assignment_id: str) -> Dict:
        """
        Delete all calendar events associated with a chore assignment.
        
        Args:
            assignment_id: The assignment ID to delete events for
        
        Returns:
            Dict with deletion results
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        try:
            event_tracking_data = self._load_event_tracking()
            
            if assignment_id not in event_tracking_data["chore_events"]:
                return {"success": False, "error": f"No tracked events found for assignment {assignment_id}"}
            
            events_to_delete = event_tracking_data["chore_events"][assignment_id]
            
            results = {
                "success": True,
                "assignment_id": assignment_id,
                "total_events": len(events_to_delete),
                "successful_deletions": 0,
                "failed_deletions": 0,
                "deletion_details": {}
            }
            
            # Delete each event
            for google_id, event_info in events_to_delete.items():
                try:
                    success = self.household_calendar.user_calendar_service.delete_chore_from_calendar(
                        google_id,
                        event_info['event_id']
                    )
                    
                    if success:
                        results["successful_deletions"] += 1
                        results["deletion_details"][google_id] = {
                            "success": True,
                            "event_id": event_info['event_id']
                        }
                    else:
                        results["failed_deletions"] += 1
                        results["deletion_details"][google_id] = {
                            "success": False,
                            "event_id": event_info['event_id'],
                            "error": "Deletion failed"
                        }
                        
                except Exception as e:
                    results["failed_deletions"] += 1
                    results["deletion_details"][google_id] = {
                        "success": False,
                        "event_id": event_info.get('event_id', 'unknown'),
                        "error": str(e)
                    }
            
            # Remove from tracking if all deletions were successful
            if results["failed_deletions"] == 0:
                del event_tracking_data["chore_events"][assignment_id]
                event_tracking_data["event_metadata"]["total_events_deleted"] += results["successful_deletions"]
                self._save_event_tracking(event_tracking_data)
            
            results["success"] = results["successful_deletions"] > 0
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Failed to delete chore events: {str(e)}"}
    
    def delete_laundry_events(self, laundry_slot_id: int) -> Dict:
        """
        Delete all calendar events associated with a laundry slot.
        
        Args:
            laundry_slot_id: The laundry slot ID to delete events for
        
        Returns:
            Dict with deletion results
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        try:
            event_tracking_data = self._load_event_tracking()
            slot_key = str(laundry_slot_id)
            
            if slot_key not in event_tracking_data["laundry_events"]:
                return {"success": False, "error": f"No tracked events found for laundry slot {laundry_slot_id}"}
            
            events_to_delete = event_tracking_data["laundry_events"][slot_key]
            
            results = {
                "success": True,
                "laundry_slot_id": laundry_slot_id,
                "total_events": len(events_to_delete),
                "successful_deletions": 0,
                "failed_deletions": 0,
                "deletion_details": {}
            }
            
            # Delete each event
            for google_id, event_info in events_to_delete.items():
                try:
                    success = self.household_calendar.user_calendar_service.delete_chore_from_calendar(
                        google_id,
                        event_info['event_id']
                    )
                    
                    if success:
                        results["successful_deletions"] += 1
                        results["deletion_details"][google_id] = {
                            "success": True,
                            "event_id": event_info['event_id']
                        }
                    else:
                        results["failed_deletions"] += 1
                        results["deletion_details"][google_id] = {
                            "success": False,
                            "event_id": event_info['event_id'],
                            "error": "Deletion failed"
                        }
                        
                except Exception as e:
                    results["failed_deletions"] += 1
                    results["deletion_details"][google_id] = {
                        "success": False,
                        "event_id": event_info.get('event_id', 'unknown'),
                        "error": str(e)
                    }
            
            # Remove from tracking if all deletions were successful
            if results["failed_deletions"] == 0:
                del event_tracking_data["laundry_events"][slot_key]
                event_tracking_data["event_metadata"]["total_events_deleted"] += results["successful_deletions"]
                self._save_event_tracking(event_tracking_data)
            
            results["success"] = results["successful_deletions"] > 0
            return results
            
        except Exception as e:
            return {"success": False, "error": f"Failed to delete laundry events: {str(e)}"}
    
    def _get_roommate_google_id(self, roommate_id: int) -> Optional[str]:
        """Get Google ID for a roommate."""
        try:
            roommates_file = self.data_dir / "roommates.json"
            if not roommates_file.exists():
                return None
            
            with open(roommates_file, 'r') as f:
                roommates = json.load(f)
            
            for roommate in roommates:
                if roommate['id'] == roommate_id:
                    return roommate.get('google_id')
            
            return None
        except Exception as e:
            print(f"Error getting roommate Google ID: {str(e)}")
            return None
    
    def _get_notification_recipients(
        self,
        notification_type: NotificationType,
        assignee_google_id: Optional[str],
        event_category: str
    ) -> List[Dict]:
        """
        Get list of recipients who should receive a specific type of notification.
        """
        try:
            authenticated_roommates = self.household_calendar.get_authenticated_roommates()
            recipients = []
            
            for roommate in authenticated_roommates:
                google_id = roommate['google_id']
                
                # Check if this user should receive this type of notification
                should_receive = self.preferences.should_send_notification(
                    google_id,
                    notification_type.value.split('_')[1],  # Extract notification type (assignment, reminder, etc.)
                    event_category
                )
                
                if should_receive:
                    recipients.append(roommate)
            
            return recipients
            
        except Exception as e:
            print(f"Error getting notification recipients: {str(e)}")
            return []
    
    def _build_chore_event_data(
        self,
        assignment: Dict,
        household_prefs: Dict,
        notification_type: NotificationType
    ) -> Dict:
        """Build base event data for a chore assignment."""
        
        # Get event appearance preferences
        appearance = household_prefs.get("event_appearance", {})
        chore_prefs = household_prefs.get("chore_notifications", {})
        
        # Build title
        emoji = appearance.get("chore_emoji", "🧹")
        title = f"{emoji} {assignment['chore_name']}"
        
        if appearance.get("include_points", True):
            title += f" ({assignment['points']} pts)"
        
        # Build description
        description_parts = [
            f"Chore: {assignment['chore_name']}",
            f"Assigned to: {assignment['roommate_name']}",
            f"Points: {assignment['points']}",
            f"Frequency: {assignment['frequency']}"
        ]
        
        if assignment.get('type'):
            description_parts.append(f"Type: {assignment['type']}")
        
        description_parts.append(f"Assigned: {assignment['assigned_date']}")
        description_parts.append("📱 Created by RoomieRoster")
        
        # Parse due date
        try:
            due_date = datetime.fromisoformat(assignment['due_date'].replace('Z', '+00:00'))
        except:
            # Fallback parsing
            due_date = datetime.fromisoformat(assignment['due_date'])
        
        return {
            "title": title,
            "description": "\n".join(description_parts),
            "due_date": due_date.isoformat(),
            "start_time": (due_date - timedelta(hours=1)).isoformat(),
            "end_time": due_date.isoformat(),
            "frequency": assignment['frequency'],
            "points": assignment['points'],
            "chore_name": assignment['chore_name'],
            "roommate_name": assignment['roommate_name'],
            "assigned_date": assignment['assigned_date']
        }
    
    def _build_laundry_blocking_event_data(self, laundry_slot: Dict, household_prefs: Dict) -> Dict:
        """Build event data for laundry time blocking."""
        
        appearance = household_prefs.get("event_appearance", {})
        
        # Build title
        emoji = appearance.get("laundry_emoji", "🧺")
        title = f"{emoji} Laundry - {laundry_slot['roommate_name']}"
        
        # Build description
        description_parts = [
            f"Laundry scheduled for {laundry_slot['roommate_name']}",
            f"Load type: {laundry_slot['load_type']}",
            f"Machine: {laundry_slot['machine_type']}",
            f"Estimated loads: {laundry_slot['estimated_loads']}"
        ]
        
        if laundry_slot.get('notes'):
            description_parts.append(f"Notes: {laundry_slot['notes']}")
        
        description_parts.append("🚫 Laundry room occupied")
        description_parts.append("📱 RoomieRoster household blocking")
        
        # Parse time slot
        date = laundry_slot['date']
        time_range = laundry_slot['time_slot']
        start_time, end_time = time_range.split('-')
        
        start_datetime = f"{date}T{start_time}:00"
        end_datetime = f"{date}T{end_time}:00"
        
        return {
            "title": title,
            "description": "\n".join(description_parts),
            "start_time": start_datetime,
            "end_time": end_datetime,
            "location": "Laundry Room",
            "load_type": laundry_slot['load_type'],
            "machine_type": laundry_slot['machine_type'],
            "roommate_name": laundry_slot['roommate_name']
        }
    
    def _customize_event_for_recipient(
        self,
        base_event: Dict,
        recipient: Dict,
        assignee_google_id: Optional[str],
        assignment: Dict
    ) -> Dict:
        """Customize event data for a specific recipient."""
        
        customized_event = base_event.copy()
        
        # Get recipient's preferences
        recipient_prefs = self.preferences.get_effective_preferences(recipient['google_id'])
        
        if recipient['google_id'] == assignee_google_id:
            # This is the assignee - full event with action items
            customized_event['summary'] = customized_event['title']
            customized_event['description'] = (
                f"🎯 Assigned to YOU\n\n{customized_event['description']}\n\n"
                f"Complete this chore by {assignment['due_date']}"
            )
        else:
            # This is an observer - informational event
            customized_event['summary'] = f"📋 {assignment['roommate_name']}: {assignment['chore_name']}"
            customized_event['description'] = (
                f"Assigned to {assignment['roommate_name']}\n\n{customized_event['description']}\n\n"
                f"📱 RoomieRoster household notification"
            )
        
        # Apply recipient-specific timing preferences
        user_settings = recipient_prefs.get("user_settings", {})
        personal_prefs = user_settings.get("personal_preferences", {})
        
        if personal_prefs.get("all_day_events", False):
            # Convert to all-day event
            due_date = datetime.fromisoformat(base_event['due_date'])
            customized_event['start'] = {'date': due_date.strftime('%Y-%m-%d')}
            customized_event['end'] = {'date': (due_date + timedelta(days=1)).strftime('%Y-%m-%d')}
        else:
            # Timed event
            customized_event['start'] = {
                'dateTime': base_event['start_time'],
                'timeZone': personal_prefs.get("timezone", "America/Los_Angeles")
            }
            customized_event['end'] = {
                'dateTime': base_event['end_time'],
                'timeZone': personal_prefs.get("timezone", "America/Los_Angeles")
            }
        
        return customized_event
    
    def _customize_blocking_event_for_recipient(
        self,
        base_event: Dict,
        recipient: Dict,
        laundry_slot: Dict
    ) -> Dict:
        """Customize laundry blocking event for a specific recipient."""
        
        customized_event = base_event.copy()
        
        # Get recipient's preferences
        recipient_prefs = self.preferences.get_effective_preferences(recipient['google_id'])
        user_settings = recipient_prefs.get("user_settings", {})
        personal_prefs = user_settings.get("personal_preferences", {})
        
        # Set up the event structure
        customized_event['summary'] = base_event['title']
        customized_event['start'] = {
            'dateTime': base_event['start_time'],
            'timeZone': personal_prefs.get("timezone", "America/Los_Angeles")
        }
        customized_event['end'] = {
            'dateTime': base_event['end_time'],
            'timeZone': personal_prefs.get("timezone", "America/Los_Angeles")
        }
        
        if base_event.get('location'):
            customized_event['location'] = base_event['location']
        
        return customized_event
    
    def get_notification_status(self) -> Dict:
        """Get comprehensive status of all calendar notifications."""
        try:
            event_tracking_data = self._load_event_tracking()
            
            # Count active events
            chore_events_count = len(event_tracking_data.get("chore_events", {}))
            laundry_events_count = len(event_tracking_data.get("laundry_events", {}))
            
            # Calculate total events across all users
            total_active_events = 0
            for assignment_events in event_tracking_data.get("chore_events", {}).values():
                total_active_events += len(assignment_events)
            for slot_events in event_tracking_data.get("laundry_events", {}).values():
                total_active_events += len(slot_events)
            
            return {
                "service_available": self.is_available,
                "active_chore_assignments": chore_events_count,
                "active_laundry_slots": laundry_events_count,
                "total_active_events": total_active_events,
                "metadata": event_tracking_data.get("event_metadata", {}),
                "household_status": self.household_calendar.get_household_calendar_status()
            }
            
        except Exception as e:
            return {"error": f"Failed to get notification status: {str(e)}"}
    
    def cleanup_orphaned_events(self) -> Dict:
        """
        Clean up calendar events that are tracked but no longer needed.
        This helps maintain data consistency.
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        try:
            event_tracking_data = self._load_event_tracking()
            
            # Load current assignments and laundry slots to compare
            current_assignments = self._get_current_assignments()
            current_laundry_slots = self._get_current_laundry_slots()
            
            cleanup_results = {
                "success": True,
                "orphaned_chore_events_removed": 0,
                "orphaned_laundry_events_removed": 0,
                "cleanup_details": []
            }
            
            # Check chore events
            chore_events = event_tracking_data.get("chore_events", {})
            orphaned_chore_assignments = []
            
            for assignment_id in list(chore_events.keys()):
                if assignment_id not in current_assignments:
                    orphaned_chore_assignments.append(assignment_id)
            
            # Remove orphaned chore events
            for assignment_id in orphaned_chore_assignments:
                deletion_result = self.delete_chore_events(assignment_id)
                if deletion_result.get("success"):
                    cleanup_results["orphaned_chore_events_removed"] += 1
                    cleanup_results["cleanup_details"].append({
                        "type": "chore",
                        "id": assignment_id,
                        "action": "removed",
                        "events_deleted": deletion_result.get("successful_deletions", 0)
                    })
            
            # Check laundry events
            laundry_events = event_tracking_data.get("laundry_events", {})
            orphaned_laundry_slots = []
            
            for slot_id in list(laundry_events.keys()):
                if int(slot_id) not in current_laundry_slots:
                    orphaned_laundry_slots.append(int(slot_id))
            
            # Remove orphaned laundry events
            for slot_id in orphaned_laundry_slots:
                deletion_result = self.delete_laundry_events(slot_id)
                if deletion_result.get("success"):
                    cleanup_results["orphaned_laundry_events_removed"] += 1
                    cleanup_results["cleanup_details"].append({
                        "type": "laundry",
                        "id": slot_id,
                        "action": "removed",
                        "events_deleted": deletion_result.get("successful_deletions", 0)
                    })
            
            return cleanup_results
            
        except Exception as e:
            return {"success": False, "error": f"Failed to cleanup orphaned events: {str(e)}"}
    
    def _get_current_assignments(self) -> List[str]:
        """Get list of current assignment IDs."""
        try:
            state_file = self.data_dir / "state.json"
            if not state_file.exists():
                return []
            
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            assignments = state.get("current_assignments", [])
            assignment_ids = []
            
            for assignment in assignments:
                assignment_id = f"{assignment['chore_id']}_{assignment['roommate_id']}_{assignment['assigned_date']}"
                assignment_ids.append(assignment_id)
            
            return assignment_ids
            
        except Exception as e:
            print(f"Error getting current assignments: {str(e)}")
            return []
    
    def _get_current_laundry_slots(self) -> List[int]:
        """Get list of current laundry slot IDs."""
        try:
            laundry_file = self.data_dir / "laundry_slots.json"
            if not laundry_file.exists():
                return []
            
            with open(laundry_file, 'r') as f:
                slots = json.load(f)
            
            return [slot['id'] for slot in slots if slot.get('status') != 'completed']
            
        except Exception as e:
            print(f"Error getting current laundry slots: {str(e)}")
            return []