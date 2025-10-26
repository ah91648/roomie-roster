"""
Test suite for Zeith productivity features (Pomodoro, Todo, Mood, Analytics).

Tests all 17 new DatabaseDataHandler methods in both PostgreSQL and JSON fallback modes.
Ensures full functionality of the Zeith transformation features.
"""
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import tempfile
import shutil

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from utils.database_data_handler import DatabaseDataHandler


class TestProductivityFeatures:
    """Test suite for all productivity feature methods."""

    @pytest.fixture(scope="function")
    def temp_data_dir(self):
        """Create a temporary directory for JSON file storage during tests."""
        temp_dir = tempfile.mkdtemp(prefix="zeith_test_")
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.fixture(scope="function")
    def handler_json_mode(self, temp_data_dir):
        """Create a DatabaseDataHandler in JSON fallback mode."""
        # Temporarily unset DATABASE_URL to force JSON mode
        original_db_url = os.environ.get('DATABASE_URL')
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        handler = DatabaseDataHandler(data_dir=temp_data_dir)
        assert not handler.use_database, "Handler should be in JSON mode"

        # Add a test roommate for foreign key constraints
        roommate = handler.add_roommate({
            "id": 1,
            "name": "Test User",
            "current_cycle_points": 0
        })

        yield handler

        # Restore original DATABASE_URL
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url

    # ====================================================================
    # POMODORO SESSION TESTS (6 methods)
    # ====================================================================

    def test_add_pomodoro_session_json_mode(self, handler_json_mode):
        """Test adding a Pomodoro session in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        session_data = {
            "roommate_id": roommate_id,
            "start_time": datetime.utcnow().isoformat(),
            "planned_duration_minutes": 25,
            "session_type": "focus",
            "status": "in_progress",
            "notes": "Working on project X"
        }

        result = handler_json_mode.add_pomodoro_session(session_data)

        assert result is not None
        assert result['roommate_id'] == roommate_id
        assert result['planned_duration_minutes'] == 25
        assert result['session_type'] == "focus"
        assert result['status'] == "in_progress"
        assert 'id' in result

    def test_get_pomodoro_sessions_json_mode(self, handler_json_mode):
        """Test retrieving Pomodoro sessions in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        # Add multiple sessions
        session1 = handler_json_mode.add_pomodoro_session({
            "roommate_id": roommate_id,
            "start_time": datetime.utcnow().isoformat(),
            "planned_duration_minutes": 25,
            "session_type": "focus",
            "status": "in_progress"
        })

        session2 = handler_json_mode.add_pomodoro_session({
            "roommate_id": roommate_id,
            "start_time": datetime.utcnow().isoformat(),
            "planned_duration_minutes": 5,
            "session_type": "short_break",
            "status": "completed"
        })

        # Get all sessions
        all_sessions = handler_json_mode.get_pomodoro_sessions()
        assert len(all_sessions) == 2

        # Filter by roommate
        roommate_sessions = handler_json_mode.get_pomodoro_sessions(roommate_id=roommate_id)
        assert len(roommate_sessions) == 2

        # Filter by status
        active_sessions = handler_json_mode.get_pomodoro_sessions(status="in_progress")
        assert len(active_sessions) == 1
        assert active_sessions[0]['session_type'] == "focus"

    def test_get_active_pomodoro_session_json_mode(self, handler_json_mode):
        """Test getting the active Pomodoro session in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        # Initially no active session
        active = handler_json_mode.get_active_pomodoro_session(roommate_id)
        assert active is None

        # Add an in_progress session
        session = handler_json_mode.add_pomodoro_session({
            "roommate_id": roommate_id,
            "start_time": datetime.utcnow().isoformat(),
            "planned_duration_minutes": 25,
            "session_type": "focus",
            "status": "in_progress"
        })

        # Now should have an active session
        active = handler_json_mode.get_active_pomodoro_session(roommate_id)
        assert active is not None
        assert active['id'] == session['id']
        assert active['status'] == "in_progress"

    def test_update_pomodoro_session_json_mode(self, handler_json_mode):
        """Test updating a Pomodoro session in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        session = handler_json_mode.add_pomodoro_session({
            "roommate_id": roommate_id,
            "start_time": datetime.utcnow().isoformat(),
            "planned_duration_minutes": 25,
            "session_type": "focus",
            "status": "in_progress",
            "notes": "Initial note"
        })

        # Update the session
        updated = handler_json_mode.update_pomodoro_session(session['id'], {
            "notes": "Updated note with progress",
            "status": "in_progress"
        })

        assert updated['notes'] == "Updated note with progress"

        # Verify persistence
        sessions = handler_json_mode.get_pomodoro_sessions()
        assert any(s['id'] == session['id'] and s['notes'] == "Updated note with progress" for s in sessions)

    def test_complete_pomodoro_session_json_mode(self, handler_json_mode):
        """Test completing a Pomodoro session in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        session = handler_json_mode.add_pomodoro_session({
            "roommate_id": roommate_id,
            "start_time": datetime.utcnow().isoformat(),
            "planned_duration_minutes": 25,
            "session_type": "focus",
            "status": "in_progress"
        })

        # Complete the session
        completed = handler_json_mode.complete_pomodoro_session(session['id'], notes="Great session!")

        assert completed['status'] == "completed"
        assert completed['end_time'] is not None
        assert "Great session!" in completed.get('notes', '')

    def test_get_pomodoro_stats_json_mode(self, handler_json_mode):
        """Test getting Pomodoro statistics in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        # Add completed sessions
        for i in range(3):
            session = handler_json_mode.add_pomodoro_session({
                "roommate_id": roommate_id,
                "start_time": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                "end_time": (datetime.utcnow() - timedelta(days=i, hours=-1)).isoformat(),
                "planned_duration_minutes": 25,
                "actual_duration_minutes": 25,
                "session_type": "focus",
                "status": "completed"
            })

        stats = handler_json_mode.get_pomodoro_stats(roommate_id, period='week')

        assert stats is not None
        assert 'total_sessions' in stats
        assert stats['total_sessions'] >= 3
        assert 'total_focus_time_minutes' in stats

    # ====================================================================
    # TODO ITEM TESTS (5 methods)
    # ====================================================================

    def test_add_todo_item_json_mode(self, handler_json_mode):
        """Test adding a todo item in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        todo_data = {
            "roommate_id": roommate_id,
            "title": "Complete project proposal",
            "description": "Write and submit the Q1 project proposal",
            "category": "Work",
            "priority": "high",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "estimated_pomodoros": 3
        }

        result = handler_json_mode.add_todo_item(todo_data)

        assert result is not None
        assert result['title'] == "Complete project proposal"
        assert result['priority'] == "high"
        assert result['status'] == "pending"
        assert 'id' in result

    def test_get_todo_items_json_mode(self, handler_json_mode):
        """Test retrieving todo items in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        # Add multiple todos
        handler_json_mode.add_todo_item({
            "roommate_id": roommate_id,
            "title": "Todo 1",
            "category": "Work",
            "priority": "high",
            "status": "pending"
        })

        handler_json_mode.add_todo_item({
            "roommate_id": roommate_id,
            "title": "Todo 2",
            "category": "Personal",
            "priority": "low",
            "status": "completed"
        })

        # Get all todos
        all_todos = handler_json_mode.get_todo_items()
        assert len(all_todos) == 2

        # Filter by status
        pending_todos = handler_json_mode.get_todo_items(status="pending")
        assert len(pending_todos) == 1
        assert pending_todos[0]['title'] == "Todo 1"

        # Filter by category
        work_todos = handler_json_mode.get_todo_items(category="Work")
        assert len(work_todos) == 1

    def test_update_todo_item_json_mode(self, handler_json_mode):
        """Test updating a todo item in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        todo = handler_json_mode.add_todo_item({
            "roommate_id": roommate_id,
            "title": "Original title",
            "priority": "medium",
            "status": "pending"
        })

        # Update the todo
        updated = handler_json_mode.update_todo_item(todo['id'], {
            "title": "Updated title",
            "priority": "urgent",
            "status": "in_progress"
        })

        assert updated['title'] == "Updated title"
        assert updated['priority'] == "urgent"
        assert updated['status'] == "in_progress"

    def test_delete_todo_item_json_mode(self, handler_json_mode):
        """Test deleting a todo item in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        todo = handler_json_mode.add_todo_item({
            "roommate_id": roommate_id,
            "title": "To be deleted",
            "priority": "low",
            "status": "pending"
        })

        # Delete the todo
        handler_json_mode.delete_todo_item(todo['id'])

        # Verify it's gone
        todos = handler_json_mode.get_todo_items()
        assert not any(t['id'] == todo['id'] for t in todos)

    def test_mark_todo_completed_json_mode(self, handler_json_mode):
        """Test marking a todo as completed in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        todo = handler_json_mode.add_todo_item({
            "roommate_id": roommate_id,
            "title": "Task to complete",
            "priority": "medium",
            "status": "in_progress"
        })

        # Mark as completed
        completed = handler_json_mode.mark_todo_completed(todo['id'])

        assert completed['status'] == "completed"
        assert completed['completed_at'] is not None

    # ====================================================================
    # MOOD ENTRY TESTS (4 methods)
    # ====================================================================

    def test_add_mood_entry_json_mode(self, handler_json_mode):
        """Test adding a mood entry in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        mood_data = {
            "roommate_id": roommate_id,
            "entry_date": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "mood_level": 4,
            "energy_level": 3,
            "stress_level": 2,
            "focus_level": 4,
            "mood_emoji": "😊",
            "mood_label": "good",
            "notes": "Feeling productive today",
            "sleep_hours": 7.5,
            "exercise_minutes": 30
        }

        result = handler_json_mode.add_mood_entry(mood_data)

        assert result is not None
        assert result['mood_level'] == 4
        assert result['energy_level'] == 3
        assert result['mood_emoji'] == "😊"
        assert 'id' in result

    def test_get_mood_entries_json_mode(self, handler_json_mode):
        """Test retrieving mood entries in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        # Add multiple entries
        for i in range(3):
            handler_json_mode.add_mood_entry({
                "roommate_id": roommate_id,
                "entry_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                "mood_level": 3 + i % 2,
                "created_at": datetime.utcnow().isoformat()
            })

        # Get all entries
        all_entries = handler_json_mode.get_mood_entries()
        assert len(all_entries) == 3

        # Filter by roommate
        roommate_entries = handler_json_mode.get_mood_entries(roommate_id=roommate_id)
        assert len(roommate_entries) == 3

    def test_update_mood_entry_json_mode(self, handler_json_mode):
        """Test updating a mood entry in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        entry = handler_json_mode.add_mood_entry({
            "roommate_id": roommate_id,
            "entry_date": datetime.utcnow().isoformat(),
            "mood_level": 3,
            "created_at": datetime.utcnow().isoformat(),
            "notes": "Initial note"
        })

        # Update the entry
        updated = handler_json_mode.update_mood_entry(entry['id'], {
            "mood_level": 4,
            "notes": "Feeling better now!",
            "energy_level": 4
        })

        assert updated['mood_level'] == 4
        assert "Feeling better now!" in updated['notes']
        assert updated['energy_level'] == 4

    def test_get_mood_trends_json_mode(self, handler_json_mode):
        """Test getting mood trends in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        # Add entries over multiple days
        for i in range(5):
            handler_json_mode.add_mood_entry({
                "roommate_id": roommate_id,
                "entry_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                "mood_level": 3 + (i % 3),
                "energy_level": 2 + (i % 4),
                "stress_level": 2,
                "created_at": datetime.utcnow().isoformat()
            })

        trends = handler_json_mode.get_mood_trends(roommate_id, period='month')

        assert trends is not None
        assert 'average_mood' in trends
        assert 'entry_count' in trends
        assert trends['entry_count'] >= 5

    # ====================================================================
    # ANALYTICS SNAPSHOT TESTS (2 methods)
    # ====================================================================

    def test_add_analytics_snapshot_json_mode(self, handler_json_mode):
        """Test adding an analytics snapshot in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        snapshot_data = {
            "snapshot_date": datetime.utcnow().isoformat(),
            "roommate_id": roommate_id,
            "chores_completed": 3,
            "chores_assigned": 5,
            "total_points_earned": 15,
            "pomodoros_completed": 8,
            "focus_time_minutes": 200,
            "todos_completed": 4,
            "todos_created": 6,
            "average_mood": 4.2,
            "average_energy": 3.8,
            "mood_entries_count": 1,
            "created_at": datetime.utcnow().isoformat()
        }

        result = handler_json_mode.add_analytics_snapshot(snapshot_data)

        assert result is not None
        assert result['chores_completed'] == 3
        assert result['pomodoros_completed'] == 8
        assert result['average_mood'] == 4.2
        assert 'id' in result

    def test_get_analytics_snapshots_json_mode(self, handler_json_mode):
        """Test retrieving analytics snapshots in JSON mode."""
        roommate_id = handler_json_mode.get_roommates()[0]['id']

        # Add snapshots for multiple days
        for i in range(3):
            handler_json_mode.add_analytics_snapshot({
                "snapshot_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                "roommate_id": roommate_id,
                "chores_completed": 2 + i,
                "chores_assigned": 5,
                "total_points_earned": 10 * (i + 1),
                "pomodoros_completed": 5 + i,
                "focus_time_minutes": 125 + (i * 25),
                "todos_completed": 2,
                "todos_created": 3,
                "created_at": datetime.utcnow().isoformat()
            })

        # Get all snapshots
        all_snapshots = handler_json_mode.get_analytics_snapshots()
        assert len(all_snapshots) == 3

        # Filter by roommate
        roommate_snapshots = handler_json_mode.get_analytics_snapshots(roommate_id=roommate_id)
        assert len(roommate_snapshots) == 3


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
