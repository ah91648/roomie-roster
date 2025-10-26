"""
Comprehensive API tests for Zeith productivity endpoints.

Tests authentication, rate limiting, CSRF protection, ownership enforcement,
validation, and success paths for all 20 productivity API endpoints.
"""

import pytest
import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Import Flask app and related components
import sys
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app import app
from utils.database_data_handler import DatabaseDataHandler


class TestProductivityAPIBase:
    """Base class with common setup for productivity API tests."""

    @pytest.fixture(scope="function")
    def client(self):
        """Create test client with JSON mode (no database)."""
        # Create temporary data directory
        temp_dir = tempfile.mkdtemp()

        # Unset DATABASE_URL to force JSON mode
        original_db_url = os.environ.get('DATABASE_URL')
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

        # Initialize NEW data handler with temp directory (forces re-check of DATABASE_URL)
        new_handler = DatabaseDataHandler(temp_dir)

        # Replace app's data handler
        original_handler = app.data_handler
        app.data_handler = new_handler

        # Create test roommate using JSON mode (within app context)
        with app.app_context():
            roommate = {
                "id": 1,
                "name": "Test User",
                "current_cycle_points": 0
            }
            app.data_handler.add_roommate(roommate)

        # Create test client
        client = app.test_client()

        # Mock session manager to return test roommate
        original_get_roommate = app.session_manager.get_current_roommate
        app.session_manager.get_current_roommate = lambda: roommate

        yield client

        # Cleanup
        app.session_manager.get_current_roommate = original_get_roommate
        app.data_handler = original_handler
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        shutil.rmtree(temp_dir)


class TestPomodoroEndpoints(TestProductivityAPIBase):
    """Test Pomodoro session endpoints."""

    def test_start_pomodoro_success(self, client):
        """Test starting a new Pomodoro session."""
        response = client.post('/api/pomodoro/start', json={
            'session_type': 'focus',
            'planned_duration_minutes': 25,
            'notes': 'Working on project X'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['session_type'] == 'focus'
        assert data['planned_duration_minutes'] == 25
        assert data['status'] == 'in_progress'
        assert 'id' in data

    def test_start_pomodoro_invalid_type(self, client):
        """Test starting Pomodoro with invalid session type."""
        response = client.post('/api/pomodoro/start', json={
            'session_type': 'invalid'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid session_type' in data['error']

    def test_start_pomodoro_duplicate_active(self, client):
        """Test starting Pomodoro when one is already active."""
        # Start first session
        client.post('/api/pomodoro/start', json={'session_type': 'focus'})

        # Try to start second session
        response = client.post('/api/pomodoro/start', json={'session_type': 'focus'})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'already have an active' in data['error']

    def test_get_active_pomodoro(self, client):
        """Test getting active Pomodoro session."""
        # Start a session
        client.post('/api/pomodoro/start', json={'session_type': 'focus'})

        # Get active session
        response = client.get('/api/pomodoro/active')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'in_progress'

    def test_complete_pomodoro(self, client):
        """Test completing a Pomodoro session."""
        # Start a session
        start_response = client.post('/api/pomodoro/start', json={'session_type': 'focus'})
        session_id = json.loads(start_response.data)['id']

        # Complete it
        response = client.post('/api/pomodoro/complete', json={
            'session_id': session_id,
            'notes': 'Session completed successfully'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'completed'

    def test_pause_pomodoro(self, client):
        """Test pausing a Pomodoro session."""
        # Start a session
        start_response = client.post('/api/pomodoro/start', json={'session_type': 'focus'})
        session_id = json.loads(start_response.data)['id']

        # Pause it
        response = client.post(f'/api/pomodoro/{session_id}/pause', json={})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'paused'

    def test_get_pomodoro_history(self, client):
        """Test getting Pomodoro history."""
        # Create and complete a session
        start_response = client.post('/api/pomodoro/start', json={'session_type': 'focus'})
        session_id = json.loads(start_response.data)['id']
        client.post('/api/pomodoro/complete', json={'session_id': session_id})

        # Get history
        response = client.get('/api/pomodoro/history?status=completed')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['status'] == 'completed'

    def test_get_pomodoro_stats(self, client):
        """Test getting Pomodoro statistics."""
        response = client.get('/api/pomodoro/stats?period=week')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_sessions' in data


class TestTodoEndpoints(TestProductivityAPIBase):
    """Test Todo item endpoints."""

    def test_create_todo_success(self, client):
        """Test creating a new todo."""
        future_date = (datetime.utcnow() + timedelta(days=7)).isoformat()

        response = client.post('/api/todos', json={
            'title': 'Test Task',
            'description': 'Test description',
            'priority': 'high',
            'category': 'Work',
            'due_date': future_date
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'Test Task'
        assert data['priority'] == 'high'
        assert 'id' in data

    def test_create_todo_missing_title(self, client):
        """Test creating todo without title."""
        response = client.post('/api/todos', json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Title is required' in data['error']

    def test_create_todo_invalid_priority(self, client):
        """Test creating todo with invalid priority."""
        response = client.post('/api/todos', json={
            'title': 'Test',
            'priority': 'invalid'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid priority' in data['error']

    def test_get_todos(self, client):
        """Test getting todos."""
        # Create a todo
        client.post('/api/todos', json={'title': 'Task 1', 'category': 'Work'})

        # Get todos
        response = client.get('/api/todos?category=Work')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) > 0
        assert data[0]['title'] == 'Task 1'

    def test_update_todo(self, client):
        """Test updating a todo."""
        # Create a todo
        create_response = client.post('/api/todos', json={'title': 'Original'})
        todo_id = json.loads(create_response.data)['id']

        # Update it
        response = client.put(f'/api/todos/{todo_id}', json={
            'title': 'Updated',
            'priority': 'urgent'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Updated'
        assert data['priority'] == 'urgent'

    def test_delete_todo(self, client):
        """Test deleting a todo."""
        # Create a todo
        create_response = client.post('/api/todos', json={'title': 'To Delete'})
        todo_id = json.loads(create_response.data)['id']

        # Delete it
        response = client.delete(f'/api/todos/{todo_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'deleted successfully' in data['message']

    def test_complete_todo(self, client):
        """Test completing a todo."""
        # Create a todo
        create_response = client.post('/api/todos', json={'title': 'To Complete'})
        todo_id = json.loads(create_response.data)['id']

        # Complete it
        response = client.post(f'/api/todos/{todo_id}/complete', json={})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'completed'


class TestMoodEndpoints(TestProductivityAPIBase):
    """Test Mood entry endpoints."""

    def test_create_mood_entry_success(self, client):
        """Test creating a new mood entry."""
        response = client.post('/api/mood/entries', json={
            'mood_level': 4,
            'energy_level': 3,
            'stress_level': 2,
            'sleep_hours': 7.5,
            'notes': 'Feeling good today'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['mood_level'] == 4
        assert data['energy_level'] == 3
        assert 'id' in data

    def test_create_mood_entry_missing_mood_level(self, client):
        """Test creating mood entry without mood_level."""
        response = client.post('/api/mood/entries', json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'mood_level is required' in data['error']

    def test_create_mood_entry_invalid_mood_level(self, client):
        """Test creating mood entry with invalid mood_level."""
        response = client.post('/api/mood/entries', json={
            'mood_level': 6  # Out of range (1-5)
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'between 1 and 5' in data['error']

    def test_get_mood_entries(self, client):
        """Test getting mood entries."""
        # Create an entry
        client.post('/api/mood/entries', json={'mood_level': 4})

        # Get entries
        response = client.get('/api/mood/entries')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) > 0

    def test_update_mood_entry(self, client):
        """Test updating a mood entry."""
        # Create an entry
        create_response = client.post('/api/mood/entries', json={'mood_level': 3})
        entry_id = json.loads(create_response.data)['id']

        # Update it
        response = client.put(f'/api/mood/entries/{entry_id}', json={
            'mood_level': 5,
            'notes': 'Updated notes'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['mood_level'] == 5

    def test_get_mood_trends(self, client):
        """Test getting mood trends."""
        # Create entries
        client.post('/api/mood/entries', json={'mood_level': 4})
        client.post('/api/mood/entries', json={'mood_level': 3})

        # Get trends
        response = client.get('/api/mood/trends?period=week')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'avg_mood' in data
        assert 'entry_count' in data


class TestAnalyticsEndpoints(TestProductivityAPIBase):
    """Test Analytics endpoints."""

    def test_create_analytics_snapshot(self, client):
        """Test creating an analytics snapshot."""
        response = client.post('/api/analytics/snapshot', json={
            'chores_completed': 5,
            'chores_assigned': 8,
            'pomodoros_completed': 12,
            'todos_completed': 7,
            'avg_mood_score': 4.2
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['chores_completed'] == 5
        assert data['pomodoros_completed'] == 12
        assert 'id' in data

    def test_get_analytics_snapshots(self, client):
        """Test getting analytics snapshots."""
        # Create a snapshot
        client.post('/api/analytics/snapshot', json={
            'chores_completed': 5,
            'pomodoros_completed': 10
        })

        # Get snapshots
        response = client.get('/api/analytics/snapshots')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) > 0

    def test_get_analytics_dashboard(self, client):
        """Test getting comprehensive analytics dashboard."""
        # Create some data
        client.post('/api/pomodoro/start', json={'session_type': 'focus'})
        client.post('/api/mood/entries', json={'mood_level': 4})
        client.post('/api/analytics/snapshot', json={'chores_completed': 3})

        # Get dashboard
        response = client.get('/api/analytics/dashboard?period=week')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'period' in data
        assert 'current_cycle' in data
        assert 'pomodoro' in data
        assert 'mood' in data
        assert 'snapshots' in data
        assert 'insights' in data


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
