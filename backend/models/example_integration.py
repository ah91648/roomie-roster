"""
Example integration of SQLAlchemy models with the existing RoomieRoster Flask application.

This file demonstrates how to modify the existing app.py to use the new SQLAlchemy models
while maintaining backward compatibility with existing API endpoints.
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from datetime import datetime
import os

# Import the new models and utilities
from models import setup_database, create_database_tables
from models.data_access import DatabaseDataHandler
from models.migration import run_migration

# Import existing utilities (these remain unchanged)
from utils.assignment_logic import ChoreAssignmentLogic
from utils.scheduler_service import SchedulerService
from utils.auth_service import AuthService
from utils.security_middleware import SecurityMiddleware
from utils.session_manager import SessionManager
from utils.calendar_service import CalendarService
from utils.user_calendar_service import UserCalendarService


def create_app(config_name='development', use_database=True):
    """
    Factory function to create Flask app with optional database integration.
    
    Args:
        config_name: Configuration environment ('development', 'testing', 'production')
        use_database: If True, use SQLAlchemy models; if False, use JSON DataHandler
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://localhost:3001"])
    
    # Basic Flask configuration
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'
    
    # Initialize data handler based on configuration
    if use_database:
        # Setup database
        db = setup_database(app, config_name)
        
        # Create tables if they don't exist
        with app.app_context():
            create_database_tables(app)
        
        # Use database data handler
        data_handler = DatabaseDataHandler()
        
        print(f"✓ Using SQLAlchemy database models ({config_name} config)")
    else:
        # Use existing JSON data handler
        from utils.data_handler import DataHandler
        data_handler = DataHandler()
        
        print("✓ Using JSON file-based data storage")
    
    # Initialize services (these work with both data handlers)
    assignment_logic = ChoreAssignmentLogic(data_handler)
    scheduler_service = SchedulerService(data_handler)
    auth_service = AuthService()
    security_middleware = SecurityMiddleware()
    session_manager = SessionManager()
    calendar_service = CalendarService()
    user_calendar_service = UserCalendarService()
    
    # Apply security middleware
    security_middleware.init_app(app)
    
    # Start scheduler
    scheduler_service.start()
    
    # Store services in app context for use in route handlers
    app.data_handler = data_handler
    app.assignment_logic = assignment_logic
    app.scheduler_service = scheduler_service
    app.auth_service = auth_service
    app.session_manager = session_manager
    app.calendar_service = calendar_service
    app.user_calendar_service = user_calendar_service
    
    # Register route handlers
    register_routes(app)
    
    return app


def register_routes(app):
    """Register all API routes with the Flask app."""
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        try:
            # Test data handler connection
            roommates = app.data_handler.get_roommates()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'data_handler': type(app.data_handler).__name__,
                'roommates_count': len(roommates)
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # Database status endpoint (only available when using database)
    @app.route('/api/database/status', methods=['GET'])
    def database_status():
        """Get database status and information."""
        if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
            return jsonify({'error': 'Database not configured'}), 400
        
        try:
            from models.config import get_database_info, check_database_connection
            
            connection_ok, connection_msg = check_database_connection(app)
            db_info = get_database_info(app)
            
            return jsonify({
                'connection_status': 'connected' if connection_ok else 'disconnected',
                'connection_message': connection_msg,
                'database_info': db_info,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            return jsonify({'error': f'Failed to get database status: {str(e)}'}), 500
    
    # Migration endpoint (only available when using database)
    @app.route('/api/database/migrate', methods=['POST'])
    def migrate_from_json():
        """Migrate data from JSON files to database."""
        if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
            return jsonify({'error': 'Database not configured'}), 400
        
        try:
            # Get migration parameters
            data = request.get_json() or {}
            json_data_dir = data.get('json_data_dir', 'data')
            create_backup = data.get('create_backup', True)
            
            # Run migration
            success = run_migration(app, json_data_dir, create_backup)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Migration completed successfully',
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Migration failed - check logs for details',
                    'timestamp': datetime.utcnow().isoformat()
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Migration failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # Roommates endpoints
    @app.route('/api/roommates', methods=['GET'])
    def get_roommates():
        """Get all roommates."""
        try:
            roommates = app.data_handler.get_roommates()
            return jsonify(roommates)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/roommates', methods=['POST'])
    @app.session_manager.login_required
    def add_roommate():
        """Add a new roommate."""
        try:
            data = request.get_json()
            if not data or not data.get('name'):
                return jsonify({'error': 'Name is required'}), 400
            
            # Generate ID for new roommate
            existing_roommates = app.data_handler.get_roommates()
            max_id = max([r.get('id', 0) for r in existing_roommates]) if existing_roommates else 0
            
            new_roommate = {
                'id': max_id + 1,
                'name': data['name'].strip(),
                'current_cycle_points': 0,
                'google_id': None,
                'google_profile_picture_url': None,
                'linked_at': None
            }
            
            result = app.data_handler.add_roommate(new_roommate)
            return jsonify(result), 201
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to add roommate: {str(e)}'}), 500
    
    # Chores endpoints
    @app.route('/api/chores', methods=['GET'])
    def get_chores():
        """Get all chores."""
        try:
            chores = app.data_handler.get_chores()
            return jsonify(chores)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/chores', methods=['POST'])
    @app.session_manager.login_required
    def add_chore():
        """Add a new chore."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Chore data is required'}), 400
            
            # Validate required fields
            required_fields = ['name', 'frequency', 'type', 'points']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Generate ID for new chore
            existing_chores = app.data_handler.get_chores()
            max_id = max([c.get('id', 0) for c in existing_chores]) if existing_chores else 0
            data['id'] = max_id + 1
            
            # Ensure sub_chores is a list
            if 'sub_chores' not in data:
                data['sub_chores'] = []
            
            result = app.data_handler.add_chore(data)
            return jsonify(result), 201
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to add chore: {str(e)}'}), 500
    
    # Assignment endpoints
    @app.route('/api/assign-chores', methods=['POST'])
    @app.session_manager.login_required
    def assign_chores():
        """Generate new chore assignments."""
        try:
            assignments = app.assignment_logic.assign_chores()
            return jsonify({
                'assignments': assignments,
                'message': f'Successfully assigned {len(assignments)} chores',
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            return jsonify({'error': f'Failed to assign chores: {str(e)}'}), 500
    
    @app.route('/api/current-assignments', methods=['GET'])
    def get_current_assignments():
        """Get current chore assignments."""
        try:
            assignments = app.data_handler.get_current_assignments()
            return jsonify(assignments)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Add more routes as needed following the same pattern...
    # Shopping list, requests, laundry, etc. can be added similarly
    
    return app


def main():
    """
    Main entry point for the application.
    
    This demonstrates how to create and run the app with database integration.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='RoomieRoster Application')
    parser.add_argument('--config', default='development', 
                       choices=['development', 'testing', 'production'],
                       help='Configuration environment')
    parser.add_argument('--use-json', action='store_true',
                       help='Use JSON files instead of database')
    parser.add_argument('--migrate', action='store_true',
                       help='Run migration from JSON to database before starting')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to run the application on')
    
    args = parser.parse_args()
    
    # Create app
    use_database = not args.use_json
    app = create_app(args.config, use_database)
    
    # Run migration if requested
    if args.migrate and use_database:
        print("Running migration from JSON to database...")
        with app.app_context():
            success = run_migration(app, 'data', create_backup=True)
            if success:
                print("✓ Migration completed successfully")
            else:
                print("✗ Migration failed - check logs for details")
                return
    
    # Start the application
    debug_mode = args.config == 'development'
    print(f"Starting RoomieRoster on port {args.port} (debug={debug_mode})")
    app.run(host='0.0.0.0', port=args.port, debug=debug_mode)


if __name__ == '__main__':
    main()


# Example usage scenarios:

"""
1. Run with database (development):
   python example_integration.py --config development

2. Run with JSON files (backward compatibility):
   python example_integration.py --use-json

3. Migrate data and run with database:
   python example_integration.py --migrate --config development

4. Run in production mode with database:
   python example_integration.py --config production --port 5000
"""