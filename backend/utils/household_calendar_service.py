import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth.exceptions
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    Credentials = None

from .user_calendar_service import UserCalendarService
from .auth_service import AuthService

class HouseholdCalendarService:
    """
    Multi-user calendar coordination service for RoomieRoster.
    Manages calendar operations across all authenticated roommates.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.user_calendar_service = UserCalendarService(data_dir)
        self.auth_service = AuthService(data_dir)
        self.is_available = GOOGLE_AVAILABLE
        
        # Thread pool for concurrent operations
        self.max_workers = 3  # Conservative to avoid rate limits
        self._lock = threading.Lock()
        
        # Rate limiting - Google Calendar API quotas
        self.requests_per_minute = 250  # Conservative limit
        self.requests_per_second = 10   # Burst limit
        self._request_times = []
        
        if not self.is_available:
            print("Google Calendar API dependencies not available for household calendar service.")
    
    def get_authenticated_roommates(self) -> List[Dict]:
        """
        Get all roommates who have authenticated Google accounts with calendar access.
        Returns list of roommates with their Google IDs and calendar status.
        """
        if not self.is_available:
            return []
        
        try:
            # Load roommates data
            roommates_file = self.data_dir / "roommates.json"
            if not roommates_file.exists():
                return []
            
            with open(roommates_file, 'r') as f:
                roommates = json.load(f)
            
            authenticated_roommates = []
            
            for roommate in roommates:
                google_id = roommate.get('google_id')
                if not google_id:
                    continue
                
                # Check if user has valid calendar credentials
                try:
                    creds = self.user_calendar_service.get_user_credentials(google_id)
                    if creds:
                        # Get user calendar config to check if sync is enabled
                        config = self.user_calendar_service.get_user_calendar_config(google_id)
                        
                        authenticated_roommates.append({
                            'roommate_id': roommate['id'],
                            'roommate_name': roommate['name'],
                            'google_id': google_id,
                            'calendar_sync_enabled': config.get('chore_sync_enabled', False),
                            'selected_calendar_id': config.get('selected_calendar_id', 'primary'),
                            'notification_preferences': config.get('reminder_settings', {}),
                            'last_sync_status': 'healthy'  # Will be updated based on actual sync attempts
                        })
                except Exception as e:
                    print(f"Error checking calendar credentials for roommate {roommate['name']}: {str(e)}")
                    authenticated_roommates.append({
                        'roommate_id': roommate['id'],
                        'roommate_name': roommate['name'],
                        'google_id': google_id,
                        'calendar_sync_enabled': False,
                        'selected_calendar_id': 'primary',
                        'notification_preferences': {},
                        'last_sync_status': f'error: {str(e)[:100]}'
                    })
            
            return authenticated_roommates
        except Exception as e:
            print(f"Error getting authenticated roommates: {str(e)}")
            return []
    
    def _rate_limit_check(self):
        """
        Implement rate limiting to respect Google Calendar API quotas.
        Uses sliding window approach for both per-minute and per-second limits.
        """
        current_time = time.time()
        
        with self._lock:
            # Clean old requests (older than 1 minute)
            self._request_times = [t for t in self._request_times if current_time - t < 60]
            
            # Check per-minute limit
            if len(self._request_times) >= self.requests_per_minute:
                sleep_time = 60 - (current_time - self._request_times[0])
                if sleep_time > 0:
                    print(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                    return self._rate_limit_check()  # Recursive call after sleep
            
            # Check per-second limit (last 10 requests)
            recent_requests = [t for t in self._request_times if current_time - t < 1]
            if len(recent_requests) >= self.requests_per_second:
                sleep_time = 1 - (current_time - recent_requests[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # Record this request
            self._request_times.append(current_time)
    
    def _execute_with_retry(self, func, *args, max_retries=3, **kwargs):
        """
        Execute a function with exponential backoff retry logic.
        Handles transient errors and rate limiting.
        """
        for attempt in range(max_retries):
            try:
                self._rate_limit_check()
                return func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit exceeded
                    wait_time = (2 ** attempt) + (time.time() % 1)  # Add jitter
                    print(f"Rate limit hit, retrying in {wait_time:.2f} seconds (attempt {attempt + 1})")
                    time.sleep(wait_time)
                elif e.resp.status in [500, 502, 503, 504]:  # Server errors
                    wait_time = (2 ** attempt) + (time.time() % 1)
                    print(f"Server error {e.resp.status}, retrying in {wait_time:.2f} seconds (attempt {attempt + 1})")
                    time.sleep(wait_time)
                else:
                    # Non-retryable error
                    raise e
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = (2 ** attempt)
                print(f"Unexpected error, retrying in {wait_time} seconds: {str(e)}")
                time.sleep(wait_time)
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    def broadcast_event_to_household(
        self, 
        event_data: Dict, 
        assignee_google_id: Optional[str] = None,
        include_assignee: bool = True,
        event_type: str = "notification"
    ) -> Dict:
        """
        Broadcast a calendar event to all authenticated roommates' calendars.
        
        Args:
            event_data: Event details (title, description, start_time, end_time, etc.)
            assignee_google_id: Google ID of the assignee (if any)
            include_assignee: Whether to include the assignee in the broadcast
            event_type: Type of event ("notification", "blocking", "reminder")
        
        Returns:
            Dict with success/failure status and details for each roommate
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        authenticated_roommates = self.get_authenticated_roommates()
        
        if not authenticated_roommates:
            return {"success": False, "error": "No authenticated roommates found"}
        
        # Filter roommates based on preferences and parameters
        target_roommates = []
        for roommate in authenticated_roommates:
            # Skip if calendar sync is disabled
            if not roommate['calendar_sync_enabled']:
                continue
            
            # Skip assignee if not including them
            if not include_assignee and roommate['google_id'] == assignee_google_id:
                continue
            
            target_roommates.append(roommate)
        
        if not target_roommates:
            return {"success": False, "error": "No target roommates for calendar sync"}
        
        results = {
            "success": True,
            "total_roommates": len(target_roommates),
            "successful_syncs": 0,
            "failed_syncs": 0,
            "details": {}
        }
        
        def sync_to_roommate_calendar(roommate):
            """Helper function to sync event to a single roommate's calendar"""
            try:
                google_id = roommate['google_id']
                
                # Customize event data based on whether this is the assignee
                customized_event = event_data.copy()
                
                if roommate['google_id'] == assignee_google_id:
                    # This is the assignee - full event details
                    customized_event['summary'] = f"🧹 {event_data.get('title', 'Chore Assignment')}"
                    customized_event['description'] = (
                        f"Assigned to you\n\n{event_data.get('description', '')}\n\n"
                        f"📱 Created by RoomieRoster"
                    )
                else:
                    # This is an observer - notification event
                    assignee_name = next(
                        (r['roommate_name'] for r in authenticated_roommates 
                         if r['google_id'] == assignee_google_id), 
                        "Someone"
                    )
                    customized_event['summary'] = f"📋 {assignee_name}: {event_data.get('title', 'Chore')}"
                    customized_event['description'] = (
                        f"Assigned to {assignee_name}\n\n{event_data.get('description', '')}\n\n"
                        f"📱 RoomieRoster household notification"
                    )
                
                # Create the event
                result = self._execute_with_retry(
                    self.user_calendar_service.sync_chore_to_calendar,
                    google_id,
                    customized_event
                )
                
                return {
                    "roommate_name": roommate['roommate_name'],
                    "google_id": google_id,
                    "success": True,
                    "event_id": result.get('event_id') if result else None,
                    "event_link": result.get('event_link') if result else None
                }
            except Exception as e:
                return {
                    "roommate_name": roommate['roommate_name'],
                    "google_id": roommate['google_id'],
                    "success": False,
                    "error": str(e)
                }
        
        # Execute calendar syncs concurrently with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all sync tasks
            future_to_roommate = {
                executor.submit(sync_to_roommate_calendar, roommate): roommate
                for roommate in target_roommates
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_roommate):
                roommate = future_to_roommate[future]
                try:
                    result = future.result()
                    results["details"][roommate['roommate_name']] = result
                    
                    if result["success"]:
                        results["successful_syncs"] += 1
                    else:
                        results["failed_syncs"] += 1
                        
                except Exception as e:
                    results["details"][roommate['roommate_name']] = {
                        "roommate_name": roommate['roommate_name'],
                        "google_id": roommate['google_id'],
                        "success": False,
                        "error": f"Thread execution error: {str(e)}"
                    }
                    results["failed_syncs"] += 1
        
        # Update overall success status
        results["success"] = results["successful_syncs"] > 0
        
        return results
    
    def broadcast_blocking_event_to_household(
        self, 
        blocking_data: Dict,
        exclude_google_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Create blocking events (like laundry time slots) on all roommates' calendars.
        
        Args:
            blocking_data: Event details for the blocking event
            exclude_google_ids: List of Google IDs to exclude from the broadcast
        
        Returns:
            Dict with success/failure status and details for each roommate
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        authenticated_roommates = self.get_authenticated_roommates()
        exclude_google_ids = exclude_google_ids or []
        
        # Filter out excluded users and those without sync enabled
        target_roommates = [
            roommate for roommate in authenticated_roommates
            if (roommate['calendar_sync_enabled'] and 
                roommate['google_id'] not in exclude_google_ids)
        ]
        
        if not target_roommates:
            return {"success": False, "error": "No target roommates for blocking event"}
        
        # Create blocking event data
        blocking_event = {
            "title": f"🧺 {blocking_data.get('title', 'Laundry Time')}",
            "description": (
                f"{blocking_data.get('description', '')}\n\n"
                f"🚫 Laundry room occupied\n"
                f"📱 RoomieRoster household blocking"
            ),
            "start_time": blocking_data.get('start_time'),
            "end_time": blocking_data.get('end_time'),
            "location": blocking_data.get('location', 'Laundry Room')
        }
        
        # Use the broadcast function but customize for blocking events
        return self.broadcast_event_to_household(
            blocking_event,
            assignee_google_id=None,  # No specific assignee for blocking events
            include_assignee=True,
            event_type="blocking"
        )
    
    def get_household_calendar_status(self) -> Dict:
        """
        Get comprehensive status of household calendar integration.
        """
        authenticated_roommates = self.get_authenticated_roommates()
        
        status = {
            "api_available": self.is_available,
            "total_roommates": len(authenticated_roommates),
            "authenticated_count": len([r for r in authenticated_roommates if r['last_sync_status'] == 'healthy']),
            "sync_enabled_count": len([r for r in authenticated_roommates if r['calendar_sync_enabled']]),
            "roommate_details": authenticated_roommates,
            "service_health": "healthy" if self.is_available else "api_unavailable"
        }
        
        # Determine overall health
        if status["authenticated_count"] == 0:
            status["service_health"] = "no_authenticated_users"
        elif status["sync_enabled_count"] == 0:
            status["service_health"] = "sync_disabled"
        elif status["sync_enabled_count"] < status["total_roommates"]:
            status["service_health"] = "partial_coverage"
        
        return status
    
    def test_household_calendar_access(self) -> Dict:
        """
        Test calendar access for all authenticated roommates.
        Useful for diagnostics and verification.
        """
        if not self.is_available:
            return {"success": False, "error": "Google Calendar API not available"}
        
        authenticated_roommates = self.get_authenticated_roommates()
        test_results = {
            "success": True,
            "total_tested": len(authenticated_roommates),
            "successful_tests": 0,
            "failed_tests": 0,
            "test_details": {}
        }
        
        for roommate in authenticated_roommates:
            try:
                # Test by getting the user's calendar list
                calendars = self.user_calendar_service.get_user_calendars(roommate['google_id'])
                test_results["test_details"][roommate['roommate_name']] = {
                    "success": True,
                    "calendar_count": len(calendars),
                    "selected_calendar": roommate['selected_calendar_id'],
                    "sync_enabled": roommate['calendar_sync_enabled']
                }
                test_results["successful_tests"] += 1
                
            except Exception as e:
                test_results["test_details"][roommate['roommate_name']] = {
                    "success": False,
                    "error": str(e),
                    "sync_enabled": roommate['calendar_sync_enabled']
                }
                test_results["failed_tests"] += 1
        
        test_results["success"] = test_results["successful_tests"] > 0
        return test_results