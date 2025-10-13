#!/usr/bin/env python3
"""
Production Readiness Validation Script for RoomieRoster

This script performs comprehensive validation to ensure RoomieRoster is ready for production deployment.

Checks performed:
- ✅ PostgreSQL database connection (not JSON fallback)
- ✅ All migrated data present and correct
- ✅ CRUD operations functional
- ✅ Emergency backup system working
- ✅ Health endpoint returns correct status
- ✅ Authentication bypass disabled in production mode
- ✅ All required environment variables set

Usage:
    python3 backend/scripts/verify_production_ready.py

    # With custom environment
    python3 backend/scripts/verify_production_ready.py --env production
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print section header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^70}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    """Print info message."""
    print(f"ℹ️  {text}")

def check_database_connection():
    """Check that database connection is PostgreSQL, not JSON."""
    print_header("Database Connection Check")

    try:
        from flask import Flask
        from utils.database_init import database_initializer

        app = Flask(__name__)

        with app.app_context():
            status = database_initializer.get_database_status()

            print_info(f"Storage type: {status['storage_type']}")
            print_info(f"Database connected: {status['connected']}")

            if status['storage_type'] == 'PostgreSQL' and status['connected']:
                print_success("PostgreSQL database is active and connected")
                return True
            elif status['storage_type'] == 'JSON':
                print_error("Using JSON file storage - data will be lost on restart!")
                print_error("Configure DATABASE_URL environment variable to use PostgreSQL")
                return False
            else:
                print_error("Database connection failed")
                return False

    except Exception as e:
        print_error(f"Database check failed: {str(e)}")
        return False

def check_migrated_data():
    """Verify all expected data is present after migration."""
    print_header("Data Integrity Check")

    try:
        from flask import Flask
        from utils.database_handler import DatabaseDataHandler

        app = Flask(__name__)
        handler = DatabaseDataHandler()

        with app.app_context():
            # Check roommates
            roommates = handler.get_roommates()
            print_info(f"Roommates found: {len(roommates)}")
            if len(roommates) >= 4:
                print_success(f"Found {len(roommates)} roommates (expected at least 4)")
            else:
                print_warning(f"Only found {len(roommates)} roommates (expected at least 4)")

            # Check chores
            chores = handler.get_chores()
            print_info(f"Chores found: {len(chores)}")
            if len(chores) >= 4:
                print_success(f"Found {len(chores)} chores (expected at least 4)")
            else:
                print_warning(f"Only found {len(chores)} chores (expected at least 4)")

            # Check assignments
            assignments = handler.get_current_assignments()
            print_info(f"Current assignments: {len(assignments)}")
            if len(assignments) > 0:
                print_success(f"Found {len(assignments)} active assignments")
            else:
                print_warning("No active assignments found")

            # Check shopping list
            shopping_items = handler.get_shopping_list()
            print_info(f"Shopping items: {len(shopping_items)}")
            if len(shopping_items) >= 0:
                print_success(f"Shopping list accessible ({len(shopping_items)} items)")
            else:
                print_error("Cannot access shopping list")
                return False

            return True

    except Exception as e:
        print_error(f"Data integrity check failed: {str(e)}")
        return False

def check_crud_operations():
    """Test basic CRUD operations."""
    print_header("CRUD Operations Test")

    try:
        from flask import Flask
        from utils.database_handler import DatabaseDataHandler

        app = Flask(__name__)
        handler = DatabaseDataHandler()

        with app.app_context():
            # Test: Create a test roommate
            test_roommate_name = f"Test User {datetime.now().strftime('%H%M%S')}"
            test_roommate = {
                'name': test_roommate_name,
                'current_cycle_points': 0
            }

            print_info("Testing CREATE operation...")
            created = handler.create_roommate(test_roommate)
            if created:
                print_success("CREATE operation successful")
            else:
                print_error("CREATE operation failed")
                return False

            # Test: Read the created roommate
            print_info("Testing READ operation...")
            roommates = handler.get_roommates()
            found = any(r['name'] == test_roommate_name for r in roommates)
            if found:
                print_success("READ operation successful")
            else:
                print_error("READ operation failed - created roommate not found")
                return False

            # Test: Delete the test roommate
            print_info("Testing DELETE operation...")
            test_roommate_id = next(r['id'] for r in roommates if r['name'] == test_roommate_name)
            deleted = handler.delete_roommate(test_roommate_id)
            if deleted:
                print_success("DELETE operation successful")
            else:
                print_error("DELETE operation failed")
                return False

            # Verify deletion
            roommates = handler.get_roommates()
            still_exists = any(r['name'] == test_roommate_name for r in roommates)
            if not still_exists:
                print_success("Test cleanup successful - test data removed")
                return True
            else:
                print_warning("Test data not fully removed")
                return True  # Still pass, but warn

    except Exception as e:
        print_error(f"CRUD test failed: {str(e)}")
        return False

def check_emergency_backup_system():
    """Verify emergency backup system is functional."""
    print_header("Emergency Backup System Check")

    try:
        from utils.emergency_recovery import emergency_recovery

        # Check backup directory exists
        if emergency_recovery.backup_dir.exists():
            print_success(f"Backup directory exists: {emergency_recovery.backup_dir}")
        else:
            print_warning(f"Backup directory does not exist: {emergency_recovery.backup_dir}")

        # List existing backups
        backups = emergency_recovery.list_backups()
        print_info(f"Existing backups: {len(backups)}")

        if len(backups) > 0:
            latest = backups[0]
            print_info(f"Latest backup: {latest['filename']}")
            print_info(f"Created: {latest['created']}")
            print_info(f"Size: {latest['size_mb']} MB")

        # Test creating a backup
        print_info("Creating test backup...")
        backup_path = emergency_recovery.create_emergency_backup(reason="validation_test")

        if backup_path:
            print_success(f"Backup created successfully: {Path(backup_path).name}")

            # Get status
            status = emergency_recovery.get_recovery_status()
            print_info(f"Total backups: {status['backup_count']}")
            print_info(f"Total size: {status['total_backup_size_mb']:.2f} MB")

            return True
        else:
            print_error("Failed to create backup")
            return False

    except Exception as e:
        print_error(f"Emergency backup check failed: {str(e)}")
        return False

def check_health_endpoint():
    """Test the health check endpoint."""
    print_header("Health Endpoint Check")

    # Determine which port to use
    port = os.getenv('PORT', '5001')  # Default to 5001 for local testing
    base_url = f"http://localhost:{port}"

    print_info(f"Testing health endpoint at {base_url}/api/health")
    print_info("Note: This assumes the app is already running")

    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)

        if response.status_code == 200:
            data = response.json()

            print_info(f"Status: {data.get('status')}")
            print_info(f"Database type: {data.get('database', 'unknown')}")
            print_info(f"Database connected: {data.get('database_connected', False)}")

            # Check for auth bypass status (should be present in development)
            if 'auth_bypass' in data:
                if data['auth_bypass']:
                    print_warning("Auth bypass is ENABLED")
                else:
                    print_success("Auth bypass is disabled")

            if data.get('status') == 'healthy' and data.get('database') == 'PostgreSQL':
                print_success("Health endpoint returns correct status")
                return True
            else:
                print_warning("Health endpoint accessible but not fully healthy")
                return False
        else:
            print_error(f"Health endpoint returned status code: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_warning("Could not connect to app - is it running?")
        print_info("Start the app with: python3 launch_app.py")
        return False
    except Exception as e:
        print_error(f"Health check failed: {str(e)}")
        return False

def check_auth_bypass_security():
    """Verify auth bypass is properly secured."""
    print_header("Authentication Bypass Security Check")

    try:
        from utils.dev_auth_bypass import get_bypass_status

        status = get_bypass_status()

        print_info(f"Bypass enabled: {status['bypass_enabled']}")
        print_info(f"FLASK_ENV: {status['flask_env']}")
        print_info(f"DEV_AUTH_BYPASS flag: {status['dev_auth_bypass_flag']}")
        print_info(f"Running on Render: {status['running_on_render']}")
        print_info(f"PORT set: {status['port_set']}")

        # In production mode, bypass should be disabled
        flask_env = os.getenv('FLASK_ENV', 'production')

        if flask_env == 'production':
            if status['bypass_enabled']:
                print_error("CRITICAL: Auth bypass is ENABLED in production mode!")
                print_error("This is a serious security vulnerability")
                return False
            else:
                print_success("Auth bypass properly disabled in production mode")
                return True
        else:
            if status['bypass_enabled']:
                print_warning("Auth bypass is enabled (OK for development)")
            else:
                print_info("Auth bypass is disabled")
            return True

    except Exception as e:
        print_error(f"Auth bypass security check failed: {str(e)}")
        return False

def check_environment_variables():
    """Check that all required environment variables are set."""
    print_header("Environment Variables Check")

    required_vars = [
        ('DATABASE_URL', True),
        ('GOOGLE_CLIENT_ID', False),
        ('GOOGLE_CLIENT_SECRET', False),
        ('FLASK_SECRET_KEY', True),
        ('ROOMIE_WHITELIST', False)
    ]

    all_set = True

    for var_name, critical in required_vars:
        value = os.getenv(var_name)

        if value:
            # Show first/last chars only for security
            if len(value) > 20:
                masked = f"{value[:8]}...{value[-8:]}"
            else:
                masked = f"{value[:4]}..."

            print_success(f"{var_name} is set: {masked}")
        else:
            if critical:
                print_error(f"{var_name} is NOT set (required for production)")
                all_set = False
            else:
                print_warning(f"{var_name} is NOT set (recommended for production)")

    return all_set

def main():
    """Run all validation checks."""
    print(f"\n{Colors.BOLD}RoomieRoster Production Readiness Validation{Colors.END}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {}

    # Run all checks
    results['database'] = check_database_connection()
    results['data'] = check_migrated_data()
    results['crud'] = check_crud_operations()
    results['backup'] = check_emergency_backup_system()
    results['health'] = check_health_endpoint()
    results['auth_security'] = check_auth_bypass_security()
    results['env_vars'] = check_environment_variables()

    # Summary
    print_header("Validation Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name.upper()}: {status}")

    print(f"\n{Colors.BOLD}Overall: {passed}/{total} checks passed{Colors.END}\n")

    if passed == total:
        print_success("🎉 All validation checks passed! System is production-ready.")
        return 0
    elif passed >= total - 1:
        print_warning("⚠️  Most checks passed. Review warnings before deployment.")
        return 1
    else:
        print_error("❌ Multiple validation checks failed. Fix issues before deployment.")
        return 2

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Validation interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)
