import sys
import os
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path for deployment compatibility
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables from .env file
from dotenv import load_dotenv
project_root = Path(backend_dir).parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")

# Set environment variable to relax OAuth scope validation
# This prevents "scope has changed" errors when using the same credentials
# across different authentication flows
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from flask import Flask, jsonify, request, send_from_directory, redirect
from flask_cors import CORS
from utils.data_handler import DataHandler
from utils.database_data_handler import DatabaseDataHandler
from utils.database_config import database_config
from utils.database_init import database_initializer
from utils.assignment_logic import ChoreAssignmentLogic
from utils.calendar_service import CalendarService
from utils.auth_service import AuthService
from utils.session_manager import SessionManager, login_required, roommate_required, csrf_protected
from utils.user_calendar_service import UserCalendarService
from utils.security_middleware import SecurityMiddleware, rate_limit, csrf_protected_enhanced, security_validated, auth_rate_limited
from utils.scheduler_service import SchedulerService

# Import calendar notification service
try:
    from utils.calendar_notification_service import CalendarNotificationService
    CALENDAR_NOTIFICATIONS_AVAILABLE = True
except ImportError:
    CALENDAR_NOTIFICATIONS_AVAILABLE = False
    CalendarNotificationService = None


# Initialize Flask app
app = Flask(__name__, static_folder='../frontend/build', static_url_path='/')

# Configure enhanced logging for better startup debugging
def configure_app_logging():
    """Configure comprehensive logging for Flask startup and errors"""
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    # Set Flask's logger level
    app.logger.setLevel(logging.INFO)
    
    # Add startup success indicator (removed before_first_request as it's deprecated)
    # Startup logging will be handled in the main block instead
    
    # Enhanced error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'Unhandled exception: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error', 'status_code': 500}), 500

configure_app_logging()

# Configure CORS for frontend integration
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", 
                   "http://localhost:5000", "http://127.0.0.1:5000", 
                   "https://roomie-roster.onrender.com"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"],
        "supports_credentials": True
    }
})

# Configure database connection
database_config.configure_flask_app(app)

# Initialize database if using PostgreSQL
if database_config.should_use_database():
    try:
        database_initializer.initialize_database(app)
        app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")
        # Don't fail startup - will fall back to JSON files

# Initialize data handler with database support
# Get the directory of this script to ensure correct data path
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")

# Use DatabaseDataHandler which automatically chooses between database and JSON files
data_handler = DatabaseDataHandler(data_dir)
assignment_logic = ChoreAssignmentLogic(data_handler)
calendar_service = CalendarService()
auth_service = AuthService()
user_calendar_service = UserCalendarService()
session_manager = SessionManager(auth_service=auth_service, data_handler=data_handler)
security_middleware = SecurityMiddleware()

# Initialize calendar notification service for household-wide notifications
household_calendar_service = None
if CALENDAR_NOTIFICATIONS_AVAILABLE:
    try:
        household_calendar_service = CalendarNotificationService(data_dir)
        print("Household calendar notification service initialized successfully")
    except Exception as e:
        print(f"Failed to initialize household calendar notification service: {str(e)}")
        household_calendar_service = None

# Initialize scheduler service for automatic cycle resets and laundry cleanup
scheduler_service = SchedulerService(assignment_logic=assignment_logic, data_handler=data_handler)

# Initialize session management and security with app
session_manager.init_app(app)
security_middleware.init_app(app)

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'status_code': 400}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found', 'status_code': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'status_code': 500}), 500

# Helper function to get next ID
def get_next_id(items):
    """Get the next available ID for a list of items."""
    if not items:
        return 1
    return max(item['id'] for item in items) + 1

def get_default_redirect_uri():
    """Get the appropriate redirect URI based on environment."""
    # Check for custom base URL override first (useful for other deployment platforms)
    base_url = os.getenv('APP_BASE_URL')
    if base_url:
        return f'{base_url.rstrip("/")}/api/auth/callback'
    
    # Check if we're running on Render - use explicit production URL
    # Render sets PORT environment variable, and we can also check for RENDER_SERVICE_NAME
    if os.getenv('RENDER_SERVICE_NAME') or (os.getenv('PORT') and not os.getenv('FLASK_ENV') == 'development'):
        # Production environment - use the known production URL
        return 'https://roomie-roster.onrender.com/api/auth/callback'
    
    # Development environment - detect the actual port being used
    port = os.getenv('PORT') or os.getenv('FLASK_RUN_PORT', '5000')
    
    # Handle common development port scenarios (5000, 5001, 5002)
    if port in ['5000', '5001', '5002']:
        return f'http://localhost:{port}/api/auth/callback'
    
    # Default fallback for development
    return 'http://localhost:5000/api/auth/callback'

def get_frontend_url():
    """Get the appropriate frontend URL based on environment."""
    # Check for custom base URL override first (useful for other deployment platforms)
    base_url = os.getenv('APP_BASE_URL')
    if base_url:
        return base_url.rstrip("/")
    
    # Check if we're running on Render - use explicit production URL
    # Render sets PORT environment variable, and we can also check for RENDER_SERVICE_NAME
    if os.getenv('RENDER_SERVICE_NAME') or (os.getenv('PORT') and not os.getenv('FLASK_ENV') == 'development'):
        # Production environment - use the known production URL
        return 'https://roomie-roster.onrender.com'
    
    # Development environment - frontend runs on port 3000
    return 'http://localhost:3000'

def validate_redirect_uri(redirect_uri):
    """Validate that the redirect URI is from a trusted source."""
    if not redirect_uri:
        return False
    
    # Allowed redirect URI patterns
    allowed_patterns = [
        # Local development
        'http://localhost:5000/api/auth/callback',
        'http://localhost:5001/api/auth/callback',
        'http://localhost:5002/api/auth/callback',
        'http://127.0.0.1:5000/api/auth/callback',
        'http://127.0.0.1:5001/api/auth/callback',
        'http://127.0.0.1:5002/api/auth/callback',
        # Production on Render
        'https://roomie-roster.onrender.com/api/auth/callback',
    ]
    
    # Check for custom base URL from environment
    base_url = os.getenv('APP_BASE_URL')
    if base_url:
        allowed_patterns.append(f'{base_url.rstrip("/")}/api/auth/callback')
    
    # Check for Render service name pattern
    render_service_name = os.getenv('RENDER_SERVICE_NAME')
    if render_service_name:
        allowed_patterns.append(f'https://{render_service_name}.onrender.com/api/auth/callback')
    
    return redirect_uri in allowed_patterns

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with database status."""
    try:
        # Get database status
        db_status = database_initializer.get_database_status()
        
        health_info = {
            'status': 'healthy',
            'message': 'RoomieRoster API is running',
            'database': db_status,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(health_info)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# Debug endpoint for OAuth configuration
@app.route('/api/debug/oauth-config', methods=['GET'])
def debug_oauth_config():
    """Debug endpoint to display current OAuth configuration."""
    try:
        current_redirect_uri = get_default_redirect_uri()
        frontend_url = get_frontend_url()
        
        # Get all possible redirect URIs for debugging
        possible_redirect_uris = [
            'http://localhost:5000/api/auth/callback',
            'http://localhost:5001/api/auth/callback', 
            'http://localhost:5002/api/auth/callback',
            'http://127.0.0.1:5000/api/auth/callback',
            'http://127.0.0.1:5001/api/auth/callback',
            'http://127.0.0.1:5002/api/auth/callback',
            'https://roomie-roster.onrender.com/api/auth/callback'
        ]
        
        # Add custom base URL if set
        base_url = os.getenv('APP_BASE_URL')
        if base_url:
            possible_redirect_uris.append(f'{base_url.rstrip("/")}/api/auth/callback')
        
        # Add Render service name pattern if set
        render_service_name = os.getenv('RENDER_SERVICE_NAME')
        if render_service_name:
            possible_redirect_uris.append(f'https://{render_service_name}.onrender.com/api/auth/callback')
        
        return jsonify({
            'current_redirect_uri': current_redirect_uri,
            'frontend_url': frontend_url,
            'environment_variables': {
                'PORT': os.getenv('PORT'),
                'FLASK_RUN_PORT': os.getenv('FLASK_RUN_PORT'),
                'APP_BASE_URL': os.getenv('APP_BASE_URL'),
                'RENDER_SERVICE_NAME': os.getenv('RENDER_SERVICE_NAME'),
                'FLASK_ENV': os.getenv('FLASK_ENV')
            },
            'all_possible_redirect_uris': possible_redirect_uris,
            'validation_status': {
                'current_uri_valid': validate_redirect_uri(current_redirect_uri)
            },
            'message': 'Add ALL the possible redirect URIs to your Google Cloud Console OAuth 2.0 client'
        })
    except Exception as e:
        return jsonify({'error': f'Debug endpoint failed: {str(e)}'}), 500

# Chores endpoints
@app.route('/api/chores', methods=['GET'])
@login_required
def get_chores():
    """Get all chores."""
    try:
        chores = data_handler.get_chores()
        return jsonify(chores)
    except Exception as e:
        print(f"Error getting chores: {e}")
        return jsonify({'error': 'Failed to get chores'}), 500

@app.route('/api/chores', methods=['POST'])
@login_required
@rate_limit('api')
@csrf_protected_enhanced
def add_chore():
    """Add a new chore."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'frequency', 'type', 'points']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate field values
        if data['frequency'] not in ['daily', 'weekly', 'bi-weekly']:
            return jsonify({'error': 'Invalid frequency. Must be daily, weekly, or bi-weekly'}), 400
        
        if data['type'] not in ['predefined', 'random']:
            return jsonify({'error': 'Invalid type. Must be predefined or random'}), 400
        
        if not isinstance(data['points'], int) or data['points'] < 1:
            return jsonify({'error': 'Points must be a positive integer'}), 400
        
        # Get existing chores and assign new ID
        chores = data_handler.get_chores()
        new_chore = {
            'id': get_next_id(chores),
            'name': data['name'],
            'frequency': data['frequency'],
            'type': data['type'],
            'points': data['points']
        }
        
        data_handler.add_chore(new_chore)
        return jsonify(new_chore), 201
        
    except Exception as e:
        print(f"Error adding chore: {e}")
        return jsonify({'error': 'Failed to add chore'}), 500

@app.route('/api/chores/<int:chore_id>', methods=['PUT'])
@login_required
@rate_limit('api')
@csrf_protected_enhanced
def update_chore(chore_id):
    """Update an existing chore."""
    try:
        data = request.get_json()

        # Validate input data
        if 'frequency' in data and data['frequency'] not in ['daily', 'weekly', 'bi-weekly']:
            return jsonify({'error': 'Invalid frequency'}), 400

        if 'type' in data and data['type'] not in ['predefined', 'random']:
            return jsonify({'error': 'Invalid type'}), 400

        if 'points' in data and (not isinstance(data['points'], int) or data['points'] < 1):
            return jsonify({'error': 'Points must be a positive integer'}), 400

        # Get existing chore to preserve fields not being updated
        chores = data_handler.get_chores()
        existing_chore = None
        for chore in chores:
            if chore['id'] == chore_id:
                existing_chore = chore
                break

        if not existing_chore:
            return jsonify({'error': 'Chore not found'}), 404

        # Build updated chore dict with all required fields
        updated_chore = {
            'id': chore_id,
            'name': data.get('name', existing_chore['name']),
            'frequency': data.get('frequency', existing_chore['frequency']),
            'type': data.get('type', existing_chore['type']),
            'points': data.get('points', existing_chore['points']),
            'sub_chores': existing_chore.get('sub_chores', [])
        }

        # Use the proper update method instead of save_chores
        result = data_handler.update_chore(chore_id, updated_chore)
        return jsonify(result)

    except ValueError as e:
        app.logger.error(f"Validation error updating chore {chore_id}: {e}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        app.logger.error(f"Error updating chore {chore_id}: {e}", exc_info=True)
        return jsonify({'error': f'Failed to update chore: {str(e)}'}), 500

@app.route('/api/chores/<int:chore_id>', methods=['DELETE'])
@login_required
@rate_limit('api')
@csrf_protected_enhanced
def delete_chore(chore_id):
    """Delete a chore."""
    try:
        app.logger.info(f"🗑️  Chore deletion requested: ID {chore_id}")
        chores = data_handler.get_chores()
        original_count = len(chores)
        app.logger.info(f"   Current chore count: {original_count}")
        
        # Check if chore exists before attempting deletion
        chore_exists = any(c['id'] == chore_id for c in chores)
        if not chore_exists:
            app.logger.warning(f"❌ Chore {chore_id} not found for deletion")
            return jsonify({'error': 'Chore not found'}), 404
        
        data_handler.delete_chore(chore_id)
        app.logger.info(f"✅ Chore {chore_id} deleted from data handler")
        
        # Check if anything was actually deleted
        new_chores = data_handler.get_chores()
        new_count = len(new_chores)
        app.logger.info(f"   New chore count: {new_count}")
        
        if new_count == original_count:
            app.logger.error(f"❌ Chore deletion failed - count unchanged: {original_count}")
            return jsonify({'error': 'Chore deletion failed'}), 500
        
        app.logger.info(f"✅ Chore {chore_id} successfully deleted (count: {original_count} → {new_count})")
        return jsonify({'message': 'Chore deleted successfully'}), 200
        
    except Exception as e:
        app.logger.error(f"❌ Error deleting chore {chore_id}: {e}")
        print(f"Error deleting chore: {e}")
        return jsonify({'error': 'Failed to delete chore'}), 500

# Sub-chore endpoints
@app.route('/api/chores/<int:chore_id>/sub-chores', methods=['GET'])
@login_required
def get_sub_chores(chore_id):
    """Get all sub-chores for a specific chore."""
    try:
        app.logger.info(f"Fetching sub-chores for chore ID: {chore_id}")
        chores = data_handler.get_chores()
        chore = next((c for c in chores if c['id'] == chore_id), None)
        
        if not chore:
            app.logger.warning(f"Chore not found: {chore_id}")
            return jsonify({'error': 'Chore not found'}), 404
        
        sub_chores = chore.get('sub_chores', [])
        app.logger.info(f"Successfully retrieved {len(sub_chores)} sub-chores for chore {chore_id}")
        return jsonify(sub_chores)
        
    except Exception as e:
        app.logger.error(f"Error getting sub-chores for chore {chore_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get sub-chores'}), 500

@app.route('/api/chores/<int:chore_id>/sub-chores', methods=['POST'])
@login_required
def add_sub_chore(chore_id):
    """Add a new sub-chore to a chore."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({'error': 'Missing required field: name'}), 400
        
        if not data['name'].strip():
            return jsonify({'error': 'Sub-chore name cannot be empty'}), 400
        
        new_sub_chore = data_handler.add_sub_chore(chore_id, data['name'].strip())
        return jsonify(new_sub_chore), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error adding sub-chore: {e}")
        return jsonify({'error': 'Failed to add sub-chore'}), 500

@app.route('/api/chores/<int:chore_id>/sub-chores/<int:sub_chore_id>', methods=['PUT'])
@login_required
def update_sub_chore(chore_id, sub_chore_id):
    """Update a sub-chore's name."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({'error': 'Missing required field: name'}), 400
        
        if not data['name'].strip():
            return jsonify({'error': 'Sub-chore name cannot be empty'}), 400
        
        updated_sub_chore = data_handler.update_sub_chore(chore_id, sub_chore_id, data['name'].strip())
        return jsonify(updated_sub_chore)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error updating sub-chore: {e}")
        return jsonify({'error': 'Failed to update sub-chore'}), 500

@app.route('/api/chores/<int:chore_id>/sub-chores/<int:sub_chore_id>', methods=['DELETE'])
@login_required
def delete_sub_chore(chore_id, sub_chore_id):
    """Delete a sub-chore from a chore."""
    try:
        data_handler.delete_sub_chore(chore_id, sub_chore_id)
        return jsonify({'message': 'Sub-chore deleted successfully'}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error deleting sub-chore: {e}")
        return jsonify({'error': 'Failed to delete sub-chore'}), 500

@app.route('/api/chores/<int:chore_id>/sub-chores/<int:sub_chore_id>/toggle', methods=['POST'])
@login_required
def toggle_sub_chore_completion(chore_id, sub_chore_id):
    """Toggle the completion status of a sub-chore in an assignment."""
    try:
        data = request.get_json()
        assignment_index = data.get('assignment_index') if data else None
        
        result = data_handler.toggle_sub_chore_completion(chore_id, sub_chore_id, assignment_index)
        return jsonify({
            'message': 'Sub-chore completion status updated',
            'result': result
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error toggling sub-chore completion: {e}")
        return jsonify({'error': 'Failed to toggle sub-chore completion'}), 500

@app.route('/api/chores/<int:chore_id>/progress', methods=['GET'])
@login_required
def get_sub_chore_progress(chore_id):
    """Get the progress of sub-chores for a specific chore assignment."""
    try:
        assignment_index = request.args.get('assignment_index', type=int)
        
        progress = data_handler.get_sub_chore_progress(chore_id, assignment_index)
        return jsonify(progress)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error getting sub-chore progress: {e}")
        return jsonify({'error': 'Failed to get sub-chore progress'}), 500

# Shopping list endpoints
@app.route('/api/shopping-list', methods=['GET'])
@login_required
def get_shopping_list():
    """Get all shopping list items or filter by status."""
    try:
        status = request.args.get('status')
        
        if status:
            items = data_handler.get_shopping_list_by_status(status)
        else:
            items = data_handler.get_shopping_list()
        
        return jsonify({
            'items': items,
            'count': len(items)
        })
    except Exception as e:
        print(f"Error getting shopping list: {e}")
        return jsonify({'error': 'Failed to get shopping list'}), 500

@app.route('/api/shopping-list', methods=['POST'])
@login_required
def add_shopping_item():
    """Add a new item to the shopping list."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['item_name', 'added_by', 'added_by_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        if not data['item_name'].strip():
            return jsonify({'error': 'Item name cannot be empty'}), 400
        
        # Create new shopping list item
        new_item = {
            'id': data_handler.get_next_shopping_item_id(),
            'item_name': data['item_name'].strip(),
            'estimated_price': data.get('estimated_price'),
            'actual_price': None,
            'brand_preference': data.get('brand_preference', '').strip() or None,
            'category': data.get('category', 'General'),
            'added_by': data['added_by'],
            'added_by_name': data['added_by_name'],
            'purchased_by': None,
            'purchased_by_name': None,
            'purchase_date': None,
            'notes': data.get('notes', '').strip() or None,
            'status': 'active',
            'date_added': __import__('datetime').datetime.now().isoformat()
        }
        
        data_handler.add_shopping_item(new_item)
        return jsonify(new_item), 201
        
    except Exception as e:
        print(f"Error adding shopping item: {e}")
        return jsonify({'error': 'Failed to add shopping item'}), 500

@app.route('/api/shopping-list/<int:item_id>', methods=['PUT'])
@login_required
def update_shopping_item(item_id):
    """Update an existing shopping list item."""
    try:
        data = request.get_json()
        items = data_handler.get_shopping_list()
        
        # Find the item to update
        item_to_update = None
        for item in items:
            if item['id'] == item_id:
                item_to_update = item
                break
        
        if not item_to_update:
            return jsonify({'error': 'Shopping list item not found'}), 404
        
        # Update fields if provided
        if 'item_name' in data:
            if not data['item_name'].strip():
                return jsonify({'error': 'Item name cannot be empty'}), 400
            item_to_update['item_name'] = data['item_name'].strip()
        
        if 'estimated_price' in data:
            item_to_update['estimated_price'] = data['estimated_price']
        
        if 'brand_preference' in data:
            item_to_update['brand_preference'] = data['brand_preference'].strip() or None
        
        if 'notes' in data:
            item_to_update['notes'] = data['notes'].strip() or None
        
        data_handler.save_shopping_list(items)
        return jsonify(item_to_update)
        
    except Exception as e:
        print(f"Error updating shopping item: {e}")
        return jsonify({'error': 'Failed to update shopping item'}), 500

@app.route('/api/shopping-list/<int:item_id>', methods=['DELETE'])
@login_required
def delete_shopping_item(item_id):
    """Delete a shopping list item."""
    try:
        items = data_handler.get_shopping_list()
        original_count = len(items)
        
        data_handler.delete_shopping_item(item_id)
        
        # Check if anything was actually deleted
        new_items = data_handler.get_shopping_list()
        if len(new_items) == original_count:
            return jsonify({'error': 'Shopping list item not found'}), 404
        
        return jsonify({'message': 'Shopping list item deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting shopping item: {e}")
        return jsonify({'error': 'Failed to delete shopping item'}), 500

@app.route('/api/shopping-list/<int:item_id>/purchase', methods=['POST'])
@login_required
def mark_item_purchased(item_id):
    """Mark a shopping list item as purchased."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['purchased_by', 'purchased_by_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        actual_price = data.get('actual_price')
        notes = data.get('notes', '').strip() or None
        
        updated_item = data_handler.mark_item_purchased(
            item_id,
            data['purchased_by'],
            data['purchased_by_name'],
            actual_price,
            notes
        )
        
        return jsonify({
            'message': 'Item marked as purchased successfully',
            'item': updated_item
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error marking item as purchased: {e}")
        return jsonify({'error': 'Failed to mark item as purchased'}), 500

@app.route('/api/shopping-list/history', methods=['GET'])
@login_required
def get_purchase_history():
    """Get purchase history for the last N days."""
    try:
        days = request.args.get('days', 30, type=int)
        
        if days < 1 or days > 365:
            return jsonify({'error': 'Days must be between 1 and 365'}), 400
        
        history = data_handler.get_purchase_history(days)
        
        return jsonify({
            'history': history,
            'count': len(history),
            'days': days
        })
        
    except Exception as e:
        print(f"Error getting purchase history: {e}")
        return jsonify({'error': 'Failed to get purchase history'}), 500

@app.route('/api/shopping-list/metadata', methods=['GET'])
@login_required
def get_shopping_list_metadata():
    """Get shopping list metadata including last modification time."""
    try:
        metadata = data_handler.get_shopping_list_metadata()
        return jsonify(metadata)
    except Exception as e:
        print(f"Error getting shopping list metadata: {e}")
        return jsonify({'error': 'Failed to get shopping list metadata'}), 500

@app.route('/api/shopping-list/clear-all-history', methods=['POST'])
@login_required
def clear_all_purchase_history():
    """Clear all purchase history - reset all purchased items to active status."""
    try:
        cleared_count = data_handler.clear_all_purchase_history()
        return jsonify({
            'message': f'Successfully cleared {cleared_count} purchased items',
            'cleared_count': cleared_count
        }), 200
    except Exception as e:
        print(f"Error clearing all purchase history: {e}")
        return jsonify({'error': 'Failed to clear purchase history'}), 500

@app.route('/api/shopping-list/clear-history-from-date', methods=['POST'])
@login_required
def clear_purchase_history_from_date():
    """Clear purchase history from a specific date onward."""
    try:
        data = request.get_json()
        
        if not data or 'from_date' not in data:
            return jsonify({'error': 'Missing required field: from_date'}), 400
        
        from_date = data['from_date']
        
        if not from_date or not from_date.strip():
            return jsonify({'error': 'from_date cannot be empty'}), 400
        
        cleared_count = data_handler.clear_purchase_history_from_date(from_date.strip())
        return jsonify({
            'message': f'Successfully cleared {cleared_count} purchased items from {from_date} onward',
            'cleared_count': cleared_count,
            'from_date': from_date
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Error clearing purchase history from date: {e}")
        return jsonify({'error': 'Failed to clear purchase history'}), 500

# Shopping categories endpoints
@app.route('/api/shopping-list/categories', methods=['GET'])
def get_shopping_categories():
    """Get all shopping categories."""
    try:
        categories = data_handler.get_shopping_categories()
        return jsonify({'categories': categories}), 200
    except Exception as e:
        app.logger.error(f"Error getting shopping categories: {e}")
        return jsonify({'error': 'Failed to get shopping categories'}), 500

@app.route('/api/shopping-list/categories', methods=['POST'])
@login_required
def add_shopping_category():
    """Add a new shopping category."""
    try:
        data = request.get_json()

        if not data or 'category_name' not in data:
            return jsonify({'error': 'Missing required field: category_name'}), 400

        category_name = data['category_name'].strip()
        if not category_name:
            return jsonify({'error': 'Category name cannot be empty'}), 400

        # Validate category name length
        if len(category_name) > 100:
            return jsonify({'error': 'Category name must be 100 characters or less'}), 400

        categories = data_handler.add_shopping_category(category_name)
        return jsonify({
            'message': f'Category "{category_name}" added successfully',
            'categories': categories
        }), 201
    except Exception as e:
        app.logger.error(f"Error adding shopping category: {e}")
        return jsonify({'error': 'Failed to add shopping category'}), 500

@app.route('/api/shopping-list/categories/<category_name>', methods=['DELETE'])
@login_required
def delete_shopping_category(category_name):
    """Delete a shopping category."""
    try:
        categories = data_handler.delete_shopping_category(category_name)
        return jsonify({
            'message': f'Category "{category_name}" deleted successfully',
            'categories': categories
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error deleting shopping category: {e}")
        return jsonify({'error': 'Failed to delete shopping category'}), 500

@app.route('/api/shopping-list/by-category', methods=['GET'])
def get_shopping_list_by_category():
    """Get shopping list items grouped by category with totals."""
    try:
        status_filter = request.args.get('status')  # optional: 'active', 'purchased'

        categorized_items = data_handler.get_shopping_list_by_category()

        # Apply status filter if provided
        if status_filter:
            for category in categorized_items:
                if status_filter == 'active':
                    categorized_items[category]['items'] = categorized_items[category]['active_items']
                elif status_filter == 'purchased':
                    categorized_items[category]['items'] = categorized_items[category]['purchased_items']

        return jsonify({'categories': categorized_items}), 200
    except Exception as e:
        app.logger.error(f"Error getting shopping list by category: {e}")
        return jsonify({'error': 'Failed to get shopping list by category'}), 500

# Request endpoints
@app.route('/api/requests', methods=['GET'])
@login_required
def get_requests():
    """Get all requests with optional status filtering."""
    try:
        status = request.args.get('status')
        user_id = request.args.get('user_id', type=int)
        
        if status:
            requests = data_handler.get_requests_by_status(status)
        elif user_id and status == 'pending_for_user':
            requests = data_handler.get_pending_requests_for_user(user_id)
        else:
            requests = data_handler.get_requests()
        
        return jsonify({'requests': requests})
    except Exception as e:
        print(f"Error getting requests: {e}")
        return jsonify({'error': 'Failed to get requests'}), 500

@app.route('/api/requests', methods=['POST'])
@login_required
def add_request():
    """Add a new request."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['item_name', 'requested_by', 'requested_by_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Set defaults
        new_request = {
            'id': data_handler.get_next_request_id(),
            'item_name': data['item_name'],
            'estimated_price': data.get('estimated_price'),
            'brand_preference': data.get('brand_preference', ''),
            'notes': data.get('notes', ''),
            'requested_by': data['requested_by'],
            'requested_by_name': data['requested_by_name'],
            'date_requested': datetime.now().isoformat(),
            'status': 'pending',
            'approvals': [],
            'approval_threshold': data.get('approval_threshold', 2),
            'auto_approve_under': data.get('auto_approve_under', 10.00),
            'final_decision_date': None,
            'final_decision_by': None,
            'final_decision_by_name': None
        }
        
        result = data_handler.add_request(new_request)
        return jsonify(result), 201
        
    except Exception as e:
        print(f"Error adding request: {e}")
        return jsonify({'error': 'Failed to add request'}), 500

@app.route('/api/requests/<int:request_id>', methods=['PUT'])
@login_required
def update_request(request_id):
    """Update an existing request."""
    try:
        data = request.get_json()
        
        # Get existing request
        requests = data_handler.get_requests()
        existing_request = None
        for r in requests:
            if r['id'] == request_id:
                existing_request = r
                break
        
        if not existing_request:
            return jsonify({'error': f'Request with id {request_id} not found'}), 404
        
        # Only allow updates if request is still pending
        if existing_request['status'] != 'pending':
            return jsonify({'error': 'Cannot update non-pending request'}), 400
        
        # Update allowed fields
        updatable_fields = ['item_name', 'estimated_price', 'brand_preference', 'notes', 'approval_threshold', 'auto_approve_under']
        for field in updatable_fields:
            if field in data:
                existing_request[field] = data[field]
        
        result = data_handler.update_request(request_id, existing_request)
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error updating request: {e}")
        return jsonify({'error': 'Failed to update request'}), 500

@app.route('/api/requests/<int:request_id>', methods=['DELETE'])
@login_required
def delete_request(request_id):
    """Delete a request."""
    try:
        data_handler.delete_request(request_id)
        return jsonify({'message': 'Request deleted successfully'})
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error deleting request: {e}")
        return jsonify({'error': 'Failed to delete request'}), 500

@app.route('/api/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_request(request_id):
    """Approve or decline a request."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['approved_by', 'approved_by_name', 'approval_status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        if data['approval_status'] not in ['approved', 'declined']:
            return jsonify({'error': 'approval_status must be "approved" or "declined"'}), 400
        
        result = data_handler.approve_request(request_id, data)
        return jsonify({'request': result, 'message': f'Request {data["approval_status"]} successfully'})
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error processing approval: {e}")
        return jsonify({'error': 'Failed to process approval'}), 500

@app.route('/api/requests/pending/<int:user_id>', methods=['GET'])
@login_required
def get_pending_requests_for_user(user_id):
    """Get pending requests that a specific user hasn't voted on yet."""
    try:
        requests = data_handler.get_pending_requests_for_user(user_id)
        return jsonify({'requests': requests, 'count': len(requests)})
        
    except Exception as e:
        print(f"Error getting pending requests for user: {e}")
        return jsonify({'error': 'Failed to get pending requests'}), 500

@app.route('/api/requests/metadata', methods=['GET'])
@login_required
def get_requests_metadata():
    """Get request metadata including last modification time."""
    try:
        metadata = data_handler.get_requests_metadata()
        return jsonify(metadata)
    except Exception as e:
        print(f"Error getting requests metadata: {e}")
        return jsonify({'error': 'Failed to get requests metadata'}), 500

# Roommates endpoints
@app.route('/api/roommates', methods=['GET'])
@login_required
def get_roommates():
    """Get all roommates."""
    try:
        roommates = data_handler.get_roommates()
        return jsonify(roommates)
    except Exception as e:
        print(f"Error getting roommates: {e}")
        return jsonify({'error': 'Failed to get roommates'}), 500

@app.route('/api/roommates', methods=['POST'])
@login_required
def add_roommate():
    """Add a new roommate."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({'error': 'Missing required field: name'}), 400
        
        # Get existing roommates and assign new ID
        roommates = data_handler.get_roommates()
        new_roommate = {
            'id': get_next_id(roommates),
            'name': data['name'],
            'current_cycle_points': 0
        }
        
        data_handler.add_roommate(new_roommate)
        return jsonify(new_roommate), 201
        
    except Exception as e:
        print(f"Error adding roommate: {e}")
        return jsonify({'error': 'Failed to add roommate'}), 500

@app.route('/api/roommates/<int:roommate_id>', methods=['PUT'])
@login_required
def update_roommate(roommate_id):
    """Update an existing roommate."""
    try:
        data = request.get_json()
        roommates = data_handler.get_roommates()
        
        # Find the roommate to update
        roommate_to_update = None
        for roommate in roommates:
            if roommate['id'] == roommate_id:
                roommate_to_update = roommate
                break
        
        if not roommate_to_update:
            return jsonify({'error': 'Roommate not found'}), 404
        
        # Update fields if provided
        if 'name' in data:
            roommate_to_update['name'] = data['name']
        if 'current_cycle_points' in data:
            if not isinstance(data['current_cycle_points'], int) or data['current_cycle_points'] < 0:
                return jsonify({'error': 'Current cycle points must be a non-negative integer'}), 400
            roommate_to_update['current_cycle_points'] = data['current_cycle_points']
        
        data_handler.save_roommates(roommates)
        return jsonify(roommate_to_update)
        
    except Exception as e:
        print(f"Error updating roommate: {e}")
        return jsonify({'error': 'Failed to update roommate'}), 500

@app.route('/api/roommates/<int:roommate_id>', methods=['DELETE'])
@login_required
def delete_roommate(roommate_id):
    """Delete a roommate and all associated data."""
    try:
        app.logger.info(f"Attempting to delete roommate with id: {roommate_id}")

        roommates = data_handler.get_roommates()
        original_count = len(roommates)

        # Attempt to delete the roommate and all associated records
        data_handler.delete_roommate(roommate_id)

        # Check if anything was actually deleted
        new_roommates = data_handler.get_roommates()
        if len(new_roommates) == original_count:
            app.logger.warning(f"Roommate {roommate_id} not found")
            return jsonify({'error': 'Roommate not found'}), 404

        app.logger.info(f"✓ Successfully deleted roommate {roommate_id}")
        return jsonify({'message': 'Roommate deleted successfully'}), 200

    except ValueError as e:
        # Handle "roommate not found" errors
        app.logger.warning(f"Roommate {roommate_id} not found: {e}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        # Log detailed error information for debugging
        app.logger.error(f"❌ Error deleting roommate {roommate_id}: {e}")
        app.logger.error(f"Full traceback:\n{traceback.format_exc()}")
        print(f"Error deleting roommate {roommate_id}: {e}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        return jsonify({'error': f'Failed to delete roommate: {str(e)}'}), 500

# Assignment endpoints
@app.route('/api/assign-chores', methods=['POST'])
@login_required
def assign_chores():
    """Trigger chore assignment logic."""
    try:
        assignments = assignment_logic.assign_chores()
        return jsonify({
            'message': 'Chores assigned successfully',
            'assignments': assignments,
            'count': len(assignments)
        })
    except Exception as e:
        print(f"Error assigning chores: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to assign chores'}), 500

@app.route('/api/current-assignments', methods=['GET'])
@login_required
def get_current_assignments():
    """Get current chore assignments."""
    try:
        assignments = data_handler.get_current_assignments()
        grouped_assignments = assignment_logic.get_assignments_by_roommate()
        
        return jsonify({
            'assignments': assignments,
            'grouped_by_roommate': grouped_assignments,
            'count': len(assignments)
        })
    except Exception as e:
        print(f"Error getting current assignments: {e}")
        return jsonify({'error': 'Failed to get current assignments'}), 500

# State management endpoints
@app.route('/api/state', methods=['GET'])
@login_required
def get_state():
    """Get application state."""
    try:
        state = data_handler.get_state()
        return jsonify(state)
    except Exception as e:
        print(f"Error getting state: {e}")
        return jsonify({'error': 'Failed to get state'}), 500

@app.route('/api/reset-cycle', methods=['POST'])
@login_required
def reset_cycle():
    """Manually reset the assignment cycle."""
    try:
        scheduler_service.manual_cycle_reset()
        return jsonify({
            'message': 'Cycle reset successfully',
            'reset_time': datetime.now().isoformat(),
            'type': 'manual'
        })
    except Exception as e:
        app.logger.error(f"Error resetting cycle: {e}", exc_info=True)
        return jsonify({'error': 'Failed to reset cycle'}), 500

@app.route('/api/scheduler/status', methods=['GET'])
@login_required
def get_scheduler_status():
    """Get the current status of the automatic scheduler."""
    try:
        status = scheduler_service.get_scheduler_status()
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"Error getting scheduler status: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get scheduler status'}), 500

# Laundry scheduling endpoints
@app.route('/api/laundry-slots', methods=['GET'])
@login_required
def get_laundry_slots():
    """Get all laundry slots with optional filtering."""
    try:
        # Check for query parameters
        date = request.args.get('date')
        roommate_id = request.args.get('roommate_id')
        status = request.args.get('status')
        include_past = request.args.get('include_past', 'false').lower() == 'true'

        # Get slots based on filters
        if date:
            slots = data_handler.get_laundry_slots_by_date(date)
        elif roommate_id:
            slots = data_handler.get_laundry_slots_by_roommate(int(roommate_id))
        elif status:
            slots = data_handler.get_laundry_slots_by_status(status)
        else:
            # By default, filter out past slots unless explicitly requested
            if include_past:
                slots = data_handler.get_laundry_slots()
            else:
                slots = data_handler.get_active_laundry_slots()

        return jsonify(slots)
    except Exception as e:
        print(f"Error getting laundry slots: {e}")
        return jsonify({'error': 'Failed to get laundry slots'}), 500

@app.route('/api/laundry-slots', methods=['POST'])
@login_required
def add_laundry_slot():
    """Add a new laundry slot."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['roommate_id', 'roommate_name', 'date', 'time_slot', 'machine_type', 'load_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate field values
        if data['machine_type'] not in ['washer', 'dryer', 'combo']:
            return jsonify({'error': 'Invalid machine_type. Must be washer, dryer, or combo'}), 400
        
        if data['load_type'] not in ['darks', 'lights', 'delicates', 'bedding', 'towels', 'mixed']:
            return jsonify({'error': 'Invalid load_type. Must be darks, lights, delicates, bedding, towels, or mixed'}), 400
        
        if not isinstance(data['roommate_id'], int) or data['roommate_id'] < 1:
            return jsonify({'error': 'roommate_id must be a positive integer'}), 400
        
        # Check for conflicts
        conflicts = data_handler.check_laundry_slot_conflicts(
            data['date'], data['time_slot'], data['machine_type']
        )
        if conflicts:
            conflict_info = conflicts[0]
            return jsonify({
                'error': 'Time slot conflict detected',
                'conflict': {
                    'existing_slot_id': conflict_info['id'],
                    'existing_roommate': conflict_info['roommate_name'],
                    'conflicting_time': conflict_info['time_slot']
                }
            }), 409
        
        # Create new laundry slot
        new_slot = {
            'id': data_handler.get_next_laundry_slot_id(),
            'roommate_id': data['roommate_id'],
            'roommate_name': data['roommate_name'],
            'date': data['date'],
            'time_slot': data['time_slot'],
            'duration_hours': data.get('duration_hours', 2),
            'load_type': data['load_type'],
            'status': 'scheduled',
            'machine_type': data['machine_type'],
            'estimated_loads': data.get('estimated_loads', 1),
            'actual_loads': 0,
            'notes': data.get('notes', ''),
            'created_date': datetime.now().isoformat(),
            'completed_date': None,
            'reminder_sent': False
        }
        
        data_handler.add_laundry_slot(new_slot)

        return jsonify(new_slot), 201
        
    except Exception as e:
        print(f"Error adding laundry slot: {e}")
        return jsonify({'error': 'Failed to add laundry slot'}), 500

@app.route('/api/laundry-slots/<int:slot_id>', methods=['PUT'])
@login_required
def update_laundry_slot(slot_id):
    """Update an existing laundry slot."""
    try:
        data = request.get_json()
        slots = data_handler.get_laundry_slots()
        
        # Find the slot to update
        slot_to_update = None
        for slot in slots:
            if slot['id'] == slot_id:
                slot_to_update = slot
                break
        
        if not slot_to_update:
            return jsonify({'error': 'Laundry slot not found'}), 404
        
        # Check for conflicts if date, time, or machine type is being changed
        if ('date' in data or 'time_slot' in data or 'machine_type' in data):
            new_date = data.get('date', slot_to_update['date'])
            new_time_slot = data.get('time_slot', slot_to_update['time_slot'])
            new_machine_type = data.get('machine_type', slot_to_update['machine_type'])
            
            conflicts = data_handler.check_laundry_slot_conflicts(
                new_date, new_time_slot, new_machine_type, exclude_slot_id=slot_id
            )
            if conflicts:
                conflict_info = conflicts[0]
                return jsonify({
                    'error': 'Time slot conflict detected',
                    'conflict': {
                        'existing_slot_id': conflict_info['id'],
                        'existing_roommate': conflict_info['roommate_name'],
                        'conflicting_time': conflict_info['time_slot']
                    }
                }), 409
        
        # Update fields if provided
        updatable_fields = ['roommate_id', 'roommate_name', 'date', 'time_slot', 'duration_hours', 
                          'load_type', 'machine_type', 'estimated_loads', 'notes', 'status']
        for field in updatable_fields:
            if field in data:
                slot_to_update[field] = data[field]
        
        data_handler.save_laundry_slots(slots)
        return jsonify(slot_to_update)
        
    except Exception as e:
        print(f"Error updating laundry slot: {e}")
        return jsonify({'error': 'Failed to update laundry slot'}), 500

@app.route('/api/laundry-slots/<int:slot_id>', methods=['DELETE'])
@login_required
def delete_laundry_slot(slot_id):
    """Delete a laundry slot."""
    try:
        # Delete the laundry slot
        data_handler.delete_laundry_slot(slot_id)
        return jsonify({'message': 'Laundry slot deleted successfully'}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error deleting laundry slot: {e}")
        return jsonify({'error': 'Failed to delete laundry slot'}), 500

@app.route('/api/laundry-slots/<int:slot_id>/complete', methods=['POST'])
@login_required
def complete_laundry_slot(slot_id):
    """Mark a laundry slot as completed."""
    try:
        data = request.get_json() or {}
        
        actual_loads = data.get('actual_loads')
        completion_notes = data.get('completion_notes', '')
        
        updated_slot = data_handler.mark_laundry_slot_completed(
            slot_id, actual_loads, completion_notes
        )

        return jsonify(updated_slot)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error completing laundry slot: {e}")
        return jsonify({'error': 'Failed to complete laundry slot'}), 500

# =============================================================================
# HOUSEHOLD CALENDAR MANAGEMENT ENDPOINTS
# =============================================================================

@app.route('/api/household-calendar/status', methods=['GET'])
@login_required
@auth_rate_limited('calendar_status')
def get_household_calendar_status():
    """Get comprehensive household calendar status."""
    try:
        if not household_calendar_service:
            return jsonify({
                'available': False,
                'error': 'Household calendar service not available'
            }), 503
        
        # Get authentication status
        auth_status = auth_service.get_household_auth_status()
        
        # Get calendar notification status
        notification_status = household_calendar_service.get_notification_status()
        
        # Combine all status information
        combined_status = {
            'service_available': True,
            'authentication': auth_status,
            'notifications': notification_status,
            'recommendations': auth_status.get('recommendations', [])
        }
        
        return jsonify(combined_status)
        
    except Exception as e:
        print(f"Error getting household calendar status: {e}")
        return jsonify({'error': 'Failed to get calendar status'}), 500

@app.route('/api/household-calendar/preferences', methods=['GET'])
@login_required
def get_user_calendar_preferences():
    """Get calendar preferences for the authenticated user."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        google_id = session_manager.get_current_user().get('google_id')
        if not google_id:
            return jsonify({'error': 'User not linked to Google account'}), 400
        
        preferences = household_calendar_service.preferences.get_user_preferences(google_id)
        effective_preferences = household_calendar_service.preferences.get_effective_preferences(google_id)
        
        return jsonify({
            'user_preferences': preferences,
            'effective_preferences': effective_preferences,
            'household_defaults': household_calendar_service.preferences.get_household_preferences()
        })
        
    except Exception as e:
        print(f"Error getting user calendar preferences: {e}")
        return jsonify({'error': 'Failed to get calendar preferences'}), 500

@app.route('/api/household-calendar/preferences', methods=['POST'])
@login_required
@csrf_protected_enhanced
def update_user_calendar_preferences():
    """Update calendar preferences for the authenticated user."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        google_id = session_manager.get_current_user().get('google_id')
        if not google_id:
            return jsonify({'error': 'User not linked to Google account'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No preferences data provided'}), 400
        
        result = household_calendar_service.preferences.update_user_preferences(google_id, data)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        print(f"Error updating user calendar preferences: {e}")
        return jsonify({'error': 'Failed to update calendar preferences'}), 500

@app.route('/api/household-calendar/household-preferences', methods=['GET'])
@login_required
@auth_rate_limited('household_prefs')
def get_household_calendar_preferences():
    """Get household-wide calendar preferences."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        preferences = household_calendar_service.preferences.get_household_preferences()
        return jsonify(preferences)
        
    except Exception as e:
        print(f"Error getting household calendar preferences: {e}")
        return jsonify({'error': 'Failed to get household preferences'}), 500

@app.route('/api/household-calendar/household-preferences', methods=['POST'])
@login_required
@roommate_required
@csrf_protected_enhanced
def update_household_calendar_preferences():
    """Update household-wide calendar preferences (admin only)."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No preferences data provided'}), 400
        
        result = household_calendar_service.preferences.update_household_preferences(data)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        print(f"Error updating household calendar preferences: {e}")
        return jsonify({'error': 'Failed to update household preferences'}), 500

@app.route('/api/household-calendar/test-access', methods=['POST'])
@login_required
@auth_rate_limited('calendar_test')
def test_household_calendar_access():
    """Test calendar access for all authenticated roommates."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        test_results = household_calendar_service.household_calendar.test_household_calendar_access()
        return jsonify(test_results)
        
    except Exception as e:
        print(f"Error testing household calendar access: {e}")
        return jsonify({'error': 'Failed to test calendar access'}), 500

@app.route('/api/household-calendar/cleanup-events', methods=['POST'])
@login_required
@roommate_required
@csrf_protected_enhanced
def cleanup_orphaned_calendar_events():
    """Clean up orphaned calendar events."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        cleanup_results = household_calendar_service.cleanup_orphaned_events()
        return jsonify(cleanup_results)
        
    except Exception as e:
        print(f"Error cleaning up calendar events: {e}")
        return jsonify({'error': 'Failed to cleanup calendar events'}), 500

@app.route('/api/household-calendar/link-roommate', methods=['POST'])
@login_required
@csrf_protected_enhanced
def link_roommate_to_google_account():
    """Link the authenticated user to a roommate account."""
    try:
        google_id = session_manager.get_current_user().get('google_id')
        if not google_id:
            return jsonify({'error': 'User not authenticated with Google'}), 400
        
        data = request.get_json()
        roommate_id = data.get('roommate_id')
        
        if not roommate_id:
            return jsonify({'error': 'roommate_id is required'}), 400
        
        result = auth_service.link_roommate_to_google_account(roommate_id, google_id)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        print(f"Error linking roommate to Google account: {e}")
        return jsonify({'error': 'Failed to link accounts'}), 500

@app.route('/api/household-calendar/unlink-roommate/<int:roommate_id>', methods=['POST'])
@login_required
@roommate_required
@csrf_protected_enhanced
def unlink_roommate_from_google_account(roommate_id):
    """Unlink a roommate from their Google account (admin only)."""
    try:
        result = auth_service.unlink_roommate_from_google_account(roommate_id)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        print(f"Error unlinking roommate from Google account: {e}")
        return jsonify({'error': 'Failed to unlink accounts'}), 500

@app.route('/api/household-calendar/sync-status', methods=['GET'])
@login_required
def get_household_calendar_sync_status():
    """Get calendar sync status for the authenticated user."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        google_id = session_manager.get_current_user().get('google_id')
        if not google_id:
            return jsonify({
                'linked': False,
                'sync_enabled': False,
                'error': 'User not linked to Google account'
            })
        
        sync_status = household_calendar_service.user_calendar_service.get_sync_status(google_id)
        return jsonify(sync_status)
        
    except Exception as e:
        print(f"Error getting user calendar sync status: {e}")
        return jsonify({'error': 'Failed to get sync status'}), 500

@app.route('/api/household-calendar/available-calendars', methods=['GET'])
@login_required
def get_user_available_calendars():
    """Get available calendars for the authenticated user."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        google_id = session_manager.get_current_user().get('google_id')
        if not google_id:
            return jsonify({'error': 'User not linked to Google account'}), 400
        
        calendars = household_calendar_service.user_calendar_service.get_user_calendars(google_id)
        return jsonify({'calendars': calendars})
        
    except Exception as e:
        print(f"Error getting user calendars: {e}")
        return jsonify({'error': 'Failed to get user calendars'}), 500

@app.route('/api/household-calendar/manual-sync', methods=['POST'])
@login_required
@csrf_protected_enhanced
@rate_limit('calendar')  # Limit manual sync
def manual_sync_user_chores():
    """Manually sync user's chores to their calendar."""
    try:
        if not household_calendar_service:
            return jsonify({'error': 'Household calendar service not available'}), 503
        
        google_id = session_manager.get_current_user().get('google_id')
        if not google_id:
            return jsonify({'error': 'User not linked to Google account'}), 400
        
        # Get current assignments for this user
        current_assignments = data_handler.get_current_assignments()
        user_assignments = [a for a in current_assignments if a.get('roommate_id') == session_manager.get_current_user().get('linked_roommate_id')]
        
        if not user_assignments:
            return jsonify({
                'success': True,
                'message': 'No current assignments to sync',
                'synced': 0
            })
        
        sync_results = household_calendar_service.user_calendar_service.sync_all_user_chores(google_id, user_assignments)
        return jsonify(sync_results)
        
    except Exception as e:
        print(f"Error manually syncing user chores: {e}")
        return jsonify({'error': 'Failed to sync chores'}), 500

@app.route('/api/laundry-slots/check-conflicts', methods=['POST'])
@login_required
def check_laundry_conflicts():
    """Check for conflicts when scheduling a laundry slot."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['date', 'time_slot', 'machine_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        exclude_slot_id = data.get('exclude_slot_id')
        
        conflicts = data_handler.check_laundry_slot_conflicts(
            data['date'], data['time_slot'], data['machine_type'], exclude_slot_id
        )
        
        return jsonify({
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts
        })
        
    except Exception as e:
        print(f"Error checking laundry conflicts: {e}")
        return jsonify({'error': 'Failed to check conflicts'}), 500

@app.route('/api/laundry-slots/metadata', methods=['GET'])
@login_required
def get_laundry_metadata():
    """Get metadata about laundry slots including last modification time."""
    try:
        metadata = data_handler.get_laundry_slots_metadata()
        return jsonify(metadata)
    except Exception as e:
        print(f"Error getting laundry metadata: {e}")
        return jsonify({'error': 'Failed to get laundry metadata'}), 500

# Blocked Time Slots endpoints
@app.route('/api/blocked-time-slots', methods=['GET'])
@login_required
def get_blocked_time_slots():
    """Get all blocked time slots."""
    try:
        blocked_slots = data_handler.get_blocked_time_slots()
        
        # Optional filtering by date
        date = request.args.get('date')
        if date:
            blocked_slots = [slot for slot in blocked_slots if slot.get('date') == date]
        
        return jsonify(blocked_slots)
    except Exception as e:
        print(f"Error getting blocked time slots: {e}")
        return jsonify({'error': 'Failed to get blocked time slots'}), 500

@app.route('/api/blocked-time-slots', methods=['POST'])
@login_required
def add_blocked_time_slot():
    """Add a new blocked time slot."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['date', 'time_slot', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add system fields
        from datetime import datetime
        blocked_slot = {
            'id': data_handler.get_next_blocked_slot_id(),
            'date': data['date'],
            'time_slot': data['time_slot'],
            'reason': data['reason'],
            'created_by': data.get('created_by', 'System'),
            'created_date': datetime.now().isoformat(),
            'sync_to_calendars': data.get('sync_to_calendars', True)
        }
        
        # Check for conflicts with existing blocked slots
        conflicts = data_handler.check_blocked_time_conflicts(
            data['date'], 
            data['time_slot'],
            blocked_slot['id']
        )
        
        if conflicts:
            return jsonify({
                'error': 'Time slot is already blocked',
                'conflicting_slot': conflicts[0]
            }), 409
        
        # Save the blocked slot
        result = data_handler.add_blocked_time_slot(blocked_slot)
        
        # Sync to calendars if requested
        if blocked_slot['sync_to_calendars']:
            try:
                sync_blocked_slot_to_calendars(blocked_slot)
            except Exception as e:
                print(f"Failed to sync blocked slot to calendars: {e}")
                # Don't fail the request if calendar sync fails
        
        return jsonify(result), 201
    except Exception as e:
        print(f"Error adding blocked time slot: {e}")
        return jsonify({'error': 'Failed to add blocked time slot'}), 500

@app.route('/api/blocked-time-slots/<int:slot_id>', methods=['PUT'])
@login_required
def update_blocked_time_slot(slot_id):
    """Update an existing blocked time slot."""
    try:
        data = request.get_json()
        blocked_slots = data_handler.get_blocked_time_slots()
        
        # Find the existing slot
        existing_slot = None
        for slot in blocked_slots:
            if slot['id'] == slot_id:
                existing_slot = slot
                break
        
        if not existing_slot:
            return jsonify({'error': 'Blocked time slot not found'}), 404
        
        # Update fields
        updated_slot = existing_slot.copy()
        updatable_fields = ['date', 'time_slot', 'reason', 'sync_to_calendars']
        for field in updatable_fields:
            if field in data:
                updated_slot[field] = data[field]
        
        from datetime import datetime
        updated_slot['updated_date'] = datetime.now().isoformat()
        
        # Check for conflicts (excluding this slot)
        if 'date' in data or 'time_slot' in data:
            conflicts = data_handler.check_blocked_time_conflicts(
                updated_slot['date'], 
                updated_slot['time_slot'],
                slot_id
            )
            
            if conflicts:
                return jsonify({
                    'error': 'Time slot conflicts with another blocked slot',
                    'conflicting_slot': conflicts[0]
                }), 409
        
        # Save the updated slot
        result = data_handler.update_blocked_time_slot(slot_id, updated_slot)
        
        # Sync to calendars if requested
        if updated_slot.get('sync_to_calendars', True):
            try:
                sync_blocked_slot_to_calendars(updated_slot)
            except Exception as e:
                print(f"Failed to sync updated blocked slot to calendars: {e}")
        
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error updating blocked time slot: {e}")
        return jsonify({'error': 'Failed to update blocked time slot'}), 500

@app.route('/api/blocked-time-slots/<int:slot_id>', methods=['DELETE'])
@login_required
def delete_blocked_time_slot(slot_id):
    """Delete a blocked time slot."""
    try:
        # Get the slot before deleting for calendar cleanup
        blocked_slots = data_handler.get_blocked_time_slots()
        slot_to_delete = None
        for slot in blocked_slots:
            if slot['id'] == slot_id:
                slot_to_delete = slot
                break
        
        if not slot_to_delete:
            return jsonify({'error': 'Blocked time slot not found'}), 404
        
        # Delete the slot
        data_handler.delete_blocked_time_slot(slot_id)
        
        # Remove from calendars if it was synced
        if slot_to_delete.get('sync_to_calendars', True):
            try:
                remove_blocked_slot_from_calendars(slot_to_delete)
            except Exception as e:
                print(f"Failed to remove blocked slot from calendars: {e}")
        
        return jsonify({'message': 'Blocked time slot deleted successfully'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error deleting blocked time slot: {e}")
        return jsonify({'error': 'Failed to delete blocked time slot'}), 500

@app.route('/api/blocked-time-slots/check-conflicts', methods=['POST'])
@login_required
def check_blocked_time_conflicts():
    """Check if a time slot conflicts with blocked slots."""
    try:
        data = request.get_json()
        
        if 'date' not in data or 'time_slot' not in data:
            return jsonify({'error': 'Missing date or time_slot'}), 400
        
        conflicts = data_handler.check_blocked_time_conflicts(
            data['date'], 
            data['time_slot'],
            data.get('exclude_slot_id')
        )
        
        return jsonify({
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts
        })
    except Exception as e:
        print(f"Error checking blocked time conflicts: {e}")
        return jsonify({'error': 'Failed to check conflicts'}), 500

# Google Calendar integration endpoints
@app.route('/api/calendar/status', methods=['GET'])
@login_required
def get_calendar_status():
    """Get calendar integration status."""
    try:
        status = calendar_service.get_status()
        return jsonify(status)
    except Exception as e:
        print(f"Error getting calendar status: {e}")
        return jsonify({'error': 'Failed to get calendar status'}), 500

@app.route('/api/calendar/setup-credentials', methods=['POST'])
@login_required
def setup_calendar_credentials():
    """Upload Google Calendar API credentials."""
    try:
        data = request.get_json()
        
        if 'credentials' not in data:
            return jsonify({'error': 'Missing credentials field'}), 400
        
        result = calendar_service.setup_credentials(data['credentials'])
        return jsonify(result), 201
        
    except Exception as e:
        print(f"Error setting up credentials: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/oauth-url', methods=['GET'])
@login_required
def get_oauth_url():
    """Get OAuth authorization URL."""
    try:
        auth_url = calendar_service.get_oauth_url()
        return jsonify({'auth_url': auth_url})
    except Exception as e:
        print(f"Error getting OAuth URL: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/callback', methods=['GET'])
@login_required
def calendar_oauth_callback():
    """Handle OAuth callback from Google."""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'Missing authorization code'}), 400
        
        result = calendar_service.handle_oauth_callback(code)
        return jsonify(result)
    except Exception as e:
        print(f"Error in OAuth callback: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/calendars', methods=['GET'])
@login_required
def get_calendar_list():
    """Get list of user's calendars."""
    try:
        calendars = calendar_service.get_calendar_list()
        return jsonify(calendars)
    except Exception as e:
        print(f"Error getting calendars: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/config', methods=['GET'])
@login_required
def get_calendar_config():
    """Get calendar integration configuration."""
    try:
        config = calendar_service.get_calendar_config()
        return jsonify(config)
    except Exception as e:
        print(f"Error getting calendar config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/config', methods=['POST'])
@login_required
def save_calendar_config():
    """Save calendar integration configuration."""
    try:
        data = request.get_json()
        result = calendar_service.save_calendar_config(data)
        return jsonify(result)
    except Exception as e:
        print(f"Error saving calendar config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/create-event', methods=['POST'])
@login_required
def create_calendar_event():
    """Create a calendar event."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['calendar_id', 'title', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        event_data = {
            'title': data['title'],
            'description': data.get('description', ''),
            'start_time': data['start_time'],
            'end_time': data['end_time'],
            'location': data.get('location', '')
        }
        
        result = calendar_service.create_event(data['calendar_id'], event_data)
        return jsonify(result), 201
        
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/delete-event', methods=['DELETE'])
@login_required
def delete_calendar_event():
    """Delete a calendar event."""
    try:
        data = request.get_json()
        
        if 'calendar_id' not in data or 'event_id' not in data:
            return jsonify({'error': 'Missing calendar_id or event_id'}), 400
        
        result = calendar_service.delete_event(data['calendar_id'], data['event_id'])
        return jsonify(result)
        
    except Exception as e:
        print(f"Error deleting calendar event: {e}")
        return jsonify({'error': str(e)}), 500

# Google Authentication endpoints
@app.route('/api/auth/status', methods=['GET'])
def get_auth_status():
    """Get authentication service status."""
    try:
        status = auth_service.get_status()
        return jsonify(status)
    except Exception as e:
        print(f"Error getting auth status: {e}")
        return jsonify({'error': 'Failed to get auth status'}), 500

@app.route('/api/auth/google-login', methods=['POST'])
@auth_rate_limited
@security_validated
def initiate_google_login():
    """Initiate Google OAuth login flow."""
    try:
        data = request.get_json() or {}
        redirect_uri = data.get('redirect_uri', get_default_redirect_uri())
        
        # Enhanced logging for debugging OAuth issues
        app.logger.info(f"🔐 OAuth Login Initiated:")
        app.logger.info(f"   Requested redirect_uri: {data.get('redirect_uri', 'None (using default)')}")
        app.logger.info(f"   Using redirect_uri: {redirect_uri}")
        app.logger.info(f"   Environment: PORT={os.getenv('PORT')}, RENDER_SERVICE_NAME={os.getenv('RENDER_SERVICE_NAME')}")
        app.logger.info(f"   APP_BASE_URL: {os.getenv('APP_BASE_URL', 'Not set')}")
        
        # Validate redirect URI for security
        if not validate_redirect_uri(redirect_uri):
            app.logger.error(f"❌ Invalid redirect URI rejected: {redirect_uri}")
            return jsonify({'error': 'Invalid redirect URI'}), 400
        
        app.logger.info(f"✅ Redirect URI validated successfully: {redirect_uri}")
        
        # Generate state token for CSRF protection
        state_token = os.urandom(32).hex()
        
        # Store state in session temporarily
        from flask import session
        session['oauth_state'] = state_token
        
        auth_url = auth_service.get_auth_url(redirect_uri, state_token)
        app.logger.info(f"🔗 Generated auth URL with redirect_uri: {redirect_uri}")
        
        return jsonify({
            'auth_url': auth_url,
            'state': state_token
        })
    except Exception as e:
        app.logger.error(f"❌ Error initiating Google login: {e}")
        print(f"Error initiating Google login: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/callback', methods=['GET'])
@auth_rate_limited
@security_validated
def handle_auth_callback():
    """Handle Google OAuth callback."""
    try:
        # Get authorization code and state from callback
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        app.logger.info(f"🔄 OAuth Callback Received:")
        app.logger.info(f"   Has code: {bool(code)}")
        app.logger.info(f"   Has state: {bool(state)}")
        app.logger.info(f"   Error param: {error}")
        app.logger.info(f"   Full URL: {request.url}")
        
        if error:
            app.logger.error(f"❌ OAuth error from Google: {error}")
            frontend_url = get_frontend_url()
            error_url = f"{frontend_url}?auth=error&message=OAuth error: {error}"
            return redirect(error_url)
        
        if not code:
            app.logger.error(f"❌ Missing authorization code in callback")
            frontend_url = get_frontend_url()
            error_url = f"{frontend_url}?auth=error&message=Missing authorization code"
            return redirect(error_url)
        
        # Verify state token for CSRF protection
        from flask import session
        if state != session.get('oauth_state'):
            frontend_url = get_frontend_url()
            error_url = f"{frontend_url}?auth=error&message=Invalid state token"
            return redirect(error_url)
        
        # Clear the state token
        session.pop('oauth_state', None)
        
        # Exchange code for tokens and get user info
        redirect_uri = request.args.get('redirect_uri', get_default_redirect_uri())
        
        # Validate redirect URI for security
        if not validate_redirect_uri(redirect_uri):
            frontend_url = get_frontend_url()
            error_url = f"{frontend_url}?auth=error&message=Invalid redirect URI"
            return redirect(error_url)
        
        result = auth_service.handle_auth_callback(code, redirect_uri, state)
        
        # Get user data for whitelist check
        user_data = result['user']
        user_email = user_data.get('email')
        
        # --- WHITELIST CHECK ---
        # Get the allowed emails from an environment variable.
        # It should be a comma-separated string: "email1@gmail.com,email2@gmail.com"
        ALLOWED_EMAILS_STR = os.environ.get('ROOMIE_WHITELIST', '')
        ALLOWED_EMAILS = [email.strip() for email in ALLOWED_EMAILS_STR.split(',') if email.strip()]
        
        if ALLOWED_EMAILS and user_email not in ALLOWED_EMAILS:
            # If the user's email is NOT in the list, deny access.
            frontend_url = get_frontend_url()
            error_url = f"{frontend_url}?auth=error&message=Access Denied. This application is private."
            return redirect(error_url)
        
        # --- If check passes, proceed with login ---
        session_created = session_manager.create_user_session(
            user_data['google_id'],
            user_data,
            remember_me=True
        )
        
        if not session_created:
            frontend_url = get_frontend_url()
            error_url = f"{frontend_url}?auth=error&message=Failed to create session"
            return redirect(error_url)
        
        # Check if user needs to link to a roommate
        current_user = session_manager.get_current_user()
        needs_linking = 'roommate' not in current_user
        
        # Redirect back to frontend with authentication status
        # Build redirect URL with query parameters for the frontend to handle
        frontend_url = get_frontend_url()
        redirect_url = f"{frontend_url}?auth=success&needs_linking={'true' if needs_linking else 'false'}"
        
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"Error in auth callback: {e}")
        # Redirect back to frontend with error
        frontend_url = get_frontend_url()
        error_url = f"{frontend_url}?auth=error&message={str(e)}"
        return redirect(error_url)

@app.route('/api/auth/profile', methods=['GET'])
@login_required
def get_user_profile():
    """Get current user profile."""
    try:
        user = session_manager.get_current_user()
        if not user:
            return jsonify({'error': 'No user session found'}), 401
        
        return jsonify({'user': user})
    except Exception as e:
        print(f"Error getting user profile: {e}")
        return jsonify({'error': 'Failed to get user profile'}), 500

@app.route('/api/auth/refresh', methods=['POST'])
@login_required
def refresh_user_session():
    """Refresh current user session."""
    try:
        success = session_manager.refresh_session()
        if not success:
            return jsonify({'error': 'Failed to refresh session'}), 401
        
        user = session_manager.get_current_user()
        return jsonify({'user': user, 'message': 'Session refreshed'})
    except Exception as e:
        print(f"Error refreshing session: {e}")
        return jsonify({'error': 'Failed to refresh session'}), 500

@app.route('/api/auth/link-roommate', methods=['POST'])
@login_required
def link_user_to_roommate():
    """Link authenticated user to an existing roommate."""
    try:
        data = request.get_json()
        
        if 'roommate_id' not in data:
            return jsonify({'error': 'Missing roommate_id'}), 400
        
        roommate_id = int(data['roommate_id'])
        
        success = session_manager.link_roommate(roommate_id)
        if not success:
            return jsonify({'error': 'Failed to link roommate. Roommate may already be linked to another account.'}), 400
        
        user = session_manager.get_current_user()
        return jsonify({
            'user': user,
            'message': 'Successfully linked to roommate'
        })
        
    except ValueError:
        return jsonify({'error': 'Invalid roommate_id'}), 400
    except Exception as e:
        print(f"Error linking roommate: {e}")
        return jsonify({'error': 'Failed to link roommate'}), 500

@app.route('/api/auth/unlink-roommate', methods=['POST'])
@login_required
def unlink_user_from_roommate():
    """Unlink authenticated user from their roommate."""
    try:
        success = session_manager.unlink_roommate()
        if not success:
            return jsonify({'error': 'Failed to unlink roommate'}), 400
        
        user = session_manager.get_current_user()
        return jsonify({
            'user': user,
            'message': 'Successfully unlinked from roommate'
        })
        
    except Exception as e:
        print(f"Error unlinking roommate: {e}")
        return jsonify({'error': 'Failed to unlink roommate'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout_user():
    """Logout current user."""
    try:
        success = session_manager.clear_session()
        if not success:
            return jsonify({'error': 'Failed to logout'}), 500
        
        return jsonify({'message': 'Successfully logged out'})
        
    except Exception as e:
        print(f"Error during logout: {e}")
        return jsonify({'error': 'Failed to logout'}), 500

@app.route('/api/auth/revoke', methods=['POST'])
@login_required
def revoke_user_access():
    """Revoke user's Google access and logout."""
    try:
        google_id = session_manager.get_current_user().get('google_id')
        if google_id:
            auth_service.revoke_user_token(google_id)
        
        session_manager.clear_session()
        
        return jsonify({'message': 'Access revoked and logged out'})
        
    except Exception as e:
        print(f"Error revoking access: {e}")
        return jsonify({'error': 'Failed to revoke access'}), 500

@app.route('/api/auth/setup-credentials', methods=['POST'])
@login_required
def setup_auth_credentials():
    """Setup Google Authentication credentials."""
    try:
        data = request.get_json()
        
        if 'credentials' not in data:
            return jsonify({'error': 'Missing credentials field'}), 400
        
        result = auth_service.setup_credentials(data['credentials'])
        return jsonify(result), 201
        
    except Exception as e:
        print(f"Error setting up auth credentials: {e}")
        return jsonify({'error': str(e)}), 500

# User Calendar Integration endpoints
@app.route('/api/user-calendar/config', methods=['GET'])
@login_required
def get_user_calendar_config():
    """Get current user's calendar configuration."""
    try:
        user = session_manager.get_current_user()
        google_id = user['google_id']
        
        config = user_calendar_service.get_user_calendar_config(google_id)
        return jsonify(config)
    except Exception as e:
        print(f"Error getting user calendar config: {e}")
        return jsonify({'error': 'Failed to get calendar configuration'}), 500

@app.route('/api/user-calendar/config', methods=['POST'])
@login_required
def save_user_calendar_config():
    """Save current user's calendar configuration."""
    try:
        user = session_manager.get_current_user()
        google_id = user['google_id']
        data = request.get_json()
        
        result = user_calendar_service.save_user_calendar_config(google_id, data)
        return jsonify(result)
    except Exception as e:
        print(f"Error saving user calendar config: {e}")
        return jsonify({'error': 'Failed to save calendar configuration'}), 500

@app.route('/api/user-calendar/calendars', methods=['GET'])
@login_required
def get_user_calendars():
    """Get current user's available calendars."""
    try:
        user = session_manager.get_current_user()
        google_id = user['google_id']
        
        calendars = user_calendar_service.get_user_calendars(google_id)
        return jsonify(calendars)
    except Exception as e:
        print(f"Error getting user calendars: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-calendar/sync-chores', methods=['POST'])
@login_required
@rate_limit('calendar')
@csrf_protected_enhanced
def sync_user_chores_to_calendar():
    """Sync current user's chore assignments to their calendar."""
    try:
        user = session_manager.get_current_user()
        google_id = user['google_id']
        
        # Get user's roommate ID to filter assignments
        if not user.get('roommate'):
            return jsonify({'error': 'User must be linked to a roommate to sync chores'}), 400
        
        roommate_id = user['roommate']['id']
        
        # Get current assignments for this user
        all_assignments = data_handler.get_current_assignments()
        user_assignments = [a for a in all_assignments if a['roommate_id'] == roommate_id]
        
        # Sync to calendar
        result = user_calendar_service.sync_all_user_chores(google_id, user_assignments)
        
        return jsonify({
            'message': f'Synced {result["synced"]} chores to calendar',
            'synced_count': result['synced'],
            'errors': result['errors'],
            'events': result.get('events', [])
        })
    except Exception as e:
        print(f"Error syncing user chores: {e}")
        return jsonify({'error': 'Failed to sync chores to calendar'}), 500

@app.route('/api/user-calendar/sync-status', methods=['GET'])
@login_required
def get_user_calendar_sync_status():
    """Get current user's calendar sync status."""
    try:
        user = session_manager.get_current_user()
        google_id = user['google_id']
        
        status = user_calendar_service.get_sync_status(google_id)
        
        # Add user-specific info
        status['has_roommate'] = bool(user.get('roommate'))
        if user.get('roommate'):
            # Count current assignments
            all_assignments = data_handler.get_current_assignments()
            user_assignments = [a for a in all_assignments if a['roommate_id'] == user['roommate']['id']]
            status['current_assignments_count'] = len(user_assignments)
        else:
            status['current_assignments_count'] = 0
        
        return jsonify(status)
    except Exception as e:
        print(f"Error getting sync status: {e}")
        return jsonify({'error': 'Failed to get sync status'}), 500

# Audit Logging endpoints
@app.route('/api/audit/logs', methods=['GET'])
@login_required
def get_audit_logs():
    """Get recent audit logs with optional filtering."""
    try:
        from utils.audit_service import AuditService

        # Check if audit logging is enabled
        if not AuditService.is_audit_enabled():
            return jsonify({
                'enabled': False,
                'message': 'Audit logging requires PostgreSQL database',
                'logs': []
            })

        # Get query parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        table_name = request.args.get('table')
        operation = request.args.get('operation')

        logs = AuditService.get_recent_logs(
            limit=limit,
            offset=offset,
            table_name=table_name,
            operation=operation
        )

        return jsonify({
            'enabled': True,
            'logs': logs,
            'count': len(logs),
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        print(f"Error getting audit logs: {e}")
        return jsonify({'error': 'Failed to get audit logs'}), 500

@app.route('/api/audit/record/<string:table_name>/<int:record_id>', methods=['GET'])
@login_required
def get_record_audit_history(table_name, record_id):
    """Get complete audit history for a specific record."""
    try:
        from utils.audit_service import AuditService

        if not AuditService.is_audit_enabled():
            return jsonify({
                'enabled': False,
                'message': 'Audit logging requires PostgreSQL database',
                'history': []
            })

        history = AuditService.get_record_history(table_name, record_id)

        return jsonify({
            'enabled': True,
            'table_name': table_name,
            'record_id': record_id,
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        print(f"Error getting record history: {e}")
        return jsonify({'error': 'Failed to get record history'}), 500

@app.route('/api/audit/user/<string:user_email>', methods=['GET'])
@login_required
def get_user_audit_activity(user_email):
    """Get audit log activity for a specific user."""
    try:
        from utils.audit_service import AuditService

        if not AuditService.is_audit_enabled():
            return jsonify({
                'enabled': False,
                'message': 'Audit logging requires PostgreSQL database',
                'activity': []
            })

        # Get query parameters
        limit = int(request.args.get('limit', 100))
        days = request.args.get('days')
        days = int(days) if days else None

        activity = AuditService.get_user_activity(
            user_email=user_email,
            limit=limit,
            days=days
        )

        return jsonify({
            'enabled': True,
            'user_email': user_email,
            'activity': activity,
            'count': len(activity)
        })
    except Exception as e:
        print(f"Error getting user activity: {e}")
        return jsonify({'error': 'Failed to get user activity'}), 500

@app.route('/api/audit/stats', methods=['GET'])
@login_required
def get_audit_statistics():
    """Get audit log statistics."""
    try:
        from utils.audit_service import AuditService

        if not AuditService.is_audit_enabled():
            return jsonify({
                'enabled': False,
                'message': 'Audit logging requires PostgreSQL database'
            })

        stats = AuditService.get_statistics()
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting audit statistics: {e}")
        return jsonify({'error': 'Failed to get audit statistics'}), 500

# Catch-all route to serve React SPA
# NOTE: These routes do NOT have @login_required because they serve the frontend.
# The frontend handles authentication checks and shows the login page.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React app for any route not defined as an API endpoint."""
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Helper functions for calendar sync
def sync_blocked_slot_to_calendars(blocked_slot):
    """Sync a blocked time slot to all users' calendars."""
    try:
        # Get all authenticated users (roommates with Google accounts)
        roommates = data_handler.get_roommates()
        authenticated_users = [rm for rm in roommates if rm.get('google_calendar_id')]
        
        if not authenticated_users:
            print("No authenticated users found for calendar sync")
            return
        
        # Create calendar event data
        event_data = create_blocked_slot_event_data(blocked_slot)
        
        # Sync to each user's calendar
        for user in authenticated_users:
            try:
                sync_to_user_calendar(user, event_data, blocked_slot)
            except Exception as e:
                print(f"Failed to sync blocked slot to {user.get('name', 'unknown')}'s calendar: {e}")
        
        print(f"Successfully synced blocked slot to {len(authenticated_users)} calendars")
        
    except Exception as e:
        print(f"Error in sync_blocked_slot_to_calendars: {e}")
        raise

def remove_blocked_slot_from_calendars(blocked_slot):
    """Remove a blocked time slot from all users' calendars."""
    try:
        # Get all authenticated users
        roommates = data_handler.get_roommates()
        authenticated_users = [rm for rm in roommates if rm.get('google_calendar_id')]
        
        if not authenticated_users:
            return
        
        # Remove from each user's calendar
        for user in authenticated_users:
            try:
                remove_from_user_calendar(user, blocked_slot)
            except Exception as e:
                print(f"Failed to remove blocked slot from {user.get('name', 'unknown')}'s calendar: {e}")
        
        print(f"Successfully removed blocked slot from {len(authenticated_users)} calendars")
        
    except Exception as e:
        print(f"Error in remove_blocked_slot_from_calendars: {e}")

def create_blocked_slot_event_data(blocked_slot):
    """Create calendar event data for a blocked time slot."""
    # Parse the time slot
    date = blocked_slot['date']
    time_range = blocked_slot['time_slot']
    start_time, end_time = time_range.split('-')
    
    # Create datetime objects
    start_datetime = f"{date}T{start_time}:00"
    end_datetime = f"{date}T{end_time}:00"
    
    return {
        'title': f"🚫 Laundry Blocked - {blocked_slot['reason']}",
        'description': f"Laundry time slot blocked by calendar settings\n" +
                      f"Reason: {blocked_slot['reason']}\n" +
                      f"Created by: {blocked_slot.get('created_by', 'System')}\n" +
                      f"This time slot is not available for laundry scheduling.",
        'start_time': start_datetime,
        'end_time': end_datetime,
        'location': 'Laundry Room',
        'blocked_slot_id': blocked_slot['id']
    }

def sync_to_user_calendar(user, event_data, blocked_slot):
    """Sync blocked slot to a specific user's calendar."""
    try:
        # Get user's calendar configuration
        calendar_id = user.get('google_calendar_id')
        if not calendar_id:
            return
        
        # Check if calendar service is available and configured
        if not calendar_service.is_configured():
            print("Calendar service not configured - skipping sync")
            return
        
        # Create the calendar event
        result = calendar_service.create_event(calendar_id, event_data)
        
        # Store the event ID for future reference (deletion)
        blocked_slot['calendar_events'] = blocked_slot.get('calendar_events', {})
        blocked_slot['calendar_events'][user['id']] = {
            'event_id': result['id'],
            'calendar_id': calendar_id,
            'user_name': user.get('name', 'Unknown')
        }
        
        print(f"Created calendar event {result['id']} for user {user.get('name')}")
        
    except Exception as e:
        print(f"Failed to sync to user calendar: {e}")
        raise

def remove_from_user_calendar(user, blocked_slot):
    """Remove blocked slot from a specific user's calendar."""
    try:
        calendar_events = blocked_slot.get('calendar_events', {})
        user_event = calendar_events.get(str(user['id']))
        
        if not user_event:
            return  # No event to remove
        
        # Check if calendar service is available
        if not calendar_service.is_configured():
            return
        
        # Delete the calendar event
        calendar_service.delete_event(
            user_event['calendar_id'], 
            user_event['event_id']
        )
        
        print(f"Removed calendar event {user_event['event_id']} for user {user.get('name')}")
        
    except Exception as e:
        print(f"Failed to remove from user calendar: {e}")

if __name__ == '__main__':
    try:
        # Get port from environment variable, default to 5000
        port = int(os.getenv('PORT', os.getenv('FLASK_RUN_PORT', 5000)))
        
        print("🏠 Starting RoomieRoster API...", flush=True)
        print(f"📍 API will be available at: http://localhost:{port}", flush=True)
        print(f"🔍 Health check: http://localhost:{port}/api/health", flush=True)
        
        # Test data handler initialization
        print("📊 Initializing data handler...", flush=True)
        with app.app_context():
            test_chores = data_handler.get_chores()
            test_roommates = data_handler.get_roommates()
            print(f"✅ Data loaded: {len(test_chores)} chores, {len(test_roommates)} roommates", flush=True)

            # Initialize scheduler for automatic cycle resets
            print("⏰ Initializing automatic scheduler...", flush=True)
            scheduler_service.init_scheduler()
            scheduler_status = scheduler_service.get_scheduler_status()
            print(f"✅ Scheduler initialized: {scheduler_status.get('status', 'unknown')}", flush=True)
            if scheduler_status.get('jobs'):
                for job in scheduler_status['jobs']:
                    print(f"   📅 Scheduled: {job['name']} - Next run: {job['next_run_time']}", flush=True)
        
        # Start Flask app
        print("🚀 Starting Flask server...", flush=True)
        app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
        
    except ImportError as e:
        print(f"❌ Import error: {e}", file=sys.stderr, flush=True)
        print("Make sure all dependencies are installed: pip install -r requirements.txt", file=sys.stderr, flush=True)
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            port = int(os.getenv('PORT', os.getenv('FLASK_RUN_PORT', 5000)))
            print(f"❌ Port {port} is already in use", file=sys.stderr, flush=True)
            print(f"Please stop the service using port {port} or use a different port", file=sys.stderr, flush=True)
        else:
            print(f"❌ OS error: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error starting Flask: {e}", file=sys.stderr, flush=True)
        print(f"Error details: {traceback.format_exc()}", file=sys.stderr, flush=True)
        sys.exit(1)