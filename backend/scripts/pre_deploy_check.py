#!/usr/bin/env python3
"""
Pre-deployment validation script for RoomieRoster.

This script catches configuration issues before deployment to prevent downtime.
Run this script before deploying to production.

Usage:
    python scripts/pre_deploy_check.py

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import sys
import os
import json
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_header(message):
    """Print section header"""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")


def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def check_environment_variables():
    """Verify all required environment variables are present"""
    print_header("Checking Environment Variables")

    required_vars = {
        'DATABASE_URL': 'PostgreSQL connection string',
        'GOOGLE_CLIENT_ID': 'Google OAuth client ID',
        'GOOGLE_CLIENT_SECRET': 'Google OAuth client secret',
        'FLASK_SECRET_KEY': 'Flask session secret key',
        'ROOMIE_WHITELIST': 'Comma-separated list of allowed email addresses'
    }

    optional_vars = {
        'APP_BASE_URL': 'Custom domain base URL',
        'FLASK_ENV': 'Flask environment (should be "production")'
    }

    all_valid = True

    # Check required variables
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value:
            print_error(f"Missing required variable: {var_name}")
            print(f"  Description: {description}")
            all_valid = False
        else:
            # Basic validation
            if var_name == 'DATABASE_URL':
                if not value.startswith('postgresql://'):
                    print_error(f"{var_name} must start with 'postgresql://'")
                    all_valid = False
                elif '?sslmode=require' not in value:
                    print_warning(f"{var_name} should include '?sslmode=require' for security")
                else:
                    print_success(f"{var_name} configured correctly")

            elif var_name == 'FLASK_SECRET_KEY':
                if len(value) < 32:
                    print_error(f"{var_name} should be at least 32 characters long")
                    all_valid = False
                elif value in ['dev', 'secret', 'change_me', 'your_secret_key_here']:
                    print_error(f"{var_name} is using a placeholder value")
                    all_valid = False
                else:
                    print_success(f"{var_name} configured")

            elif var_name == 'ROOMIE_WHITELIST':
                emails = [e.strip() for e in value.split(',')]
                if len(emails) < 1:
                    print_error(f"{var_name} must contain at least one email")
                    all_valid = False
                elif not all('@' in email for email in emails):
                    print_error(f"{var_name} contains invalid email addresses")
                    all_valid = False
                else:
                    print_success(f"{var_name} configured with {len(emails)} email(s)")

            else:
                print_success(f"{var_name} configured")

    # Check optional variables
    print("\nOptional variables:")
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value:
            if var_name == 'FLASK_ENV' and value != 'production':
                print_warning(f"{var_name} = '{value}' (should be 'production' for deployment)")
            else:
                print_success(f"{var_name} = '{value[:50]}...' " if len(value) > 50 else f"{var_name} = '{value}'")
        else:
            print(f"  {var_name}: Not set ({description})")

    return all_valid


def check_database_connection():
    """Test database connectivity"""
    print_header("Checking Database Connection")

    try:
        from flask import Flask
        from utils.database_config import db, database_config
        from sqlalchemy import text

        app = Flask(__name__)
        db_url = database_config.get_database_url()

        if not db_url:
            print_error("DATABASE_URL not configured")
            return False

        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)

        with app.app_context():
            db.session.execute(text("SELECT 1"))
            print_success("Database connection successful")

            # Test query performance
            import time
            start = time.time()
            db.session.execute(text("SELECT COUNT(*) FROM information_schema.tables"))
            elapsed = time.time() - start

            if elapsed > 1.0:
                print_warning(f"Database query slow ({elapsed:.2f}s) - check connection latency")
            else:
                print_success(f"Database query fast ({elapsed:.3f}s)")

            return True

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        print("  Ensure DATABASE_URL is correct and database is accessible")
        return False


def check_migrations():
    """Verify no pending migrations"""
    print_header("Checking Migration Status")

    try:
        from flask import Flask
        from flask_migrate import Migrate
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from utils.database_config import db, database_config

        app = Flask(__name__)
        db_url = database_config.get_database_url()

        if not db_url:
            print_error("DATABASE_URL not configured - cannot check migrations")
            return False

        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)

        migrations_dir = backend_dir / 'migrations'
        migrate = Migrate(app, db, directory=str(migrations_dir))

        with app.app_context():
            config = migrate.get_config()
            script = ScriptDirectory.from_config(config)

            with db.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()

            head_rev = script.get_current_head()

            print(f"Current revision: {current_rev or 'None'}")
            print(f"Latest revision:  {head_rev or 'None'}")

            if current_rev == head_rev:
                print_success("All migrations applied - database is up-to-date")
                return True
            else:
                print_warning("Pending migrations detected")
                print("  Run: python scripts/run_migrations.py")
                return False

    except Exception as e:
        print_warning(f"Migration check failed: {e}")
        print("  Migrations may not be initialized yet (first deployment)")
        return True  # Don't fail on first deployment


def check_frontend_build():
    """Verify frontend build exists and is valid"""
    print_header("Checking Frontend Build")

    frontend_dir = backend_dir.parent / 'frontend'
    build_dir = frontend_dir / 'build'

    if not build_dir.exists():
        print_error("Frontend build directory not found")
        print(f"  Expected: {build_dir}")
        print("  Run: cd frontend && npm run build")
        return False

    # Check for critical files
    critical_files = [
        'index.html',
        'static/js',
        'static/css'
    ]

    all_exist = True
    for file_path in critical_files:
        full_path = build_dir / file_path
        if not full_path.exists():
            print_error(f"Missing: {file_path}")
            all_exist = False

    if all_exist:
        print_success("Frontend build files present")

        # Check build size
        import subprocess
        try:
            result = subprocess.run(
                ['du', '-sh', str(build_dir)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                size = result.stdout.split()[0]
                print_success(f"Build size: {size}")
        except:
            pass

        return True

    return False


def check_security_configuration():
    """Verify security settings"""
    print_header("Checking Security Configuration")

    all_valid = True

    # Check Flask environment
    flask_env = os.getenv('FLASK_ENV')
    if flask_env != 'production':
        print_warning(f"FLASK_ENV = '{flask_env}' (should be 'production')")

    # Check debug mode
    flask_debug = os.getenv('FLASK_DEBUG')
    if flask_debug and flask_debug.lower() in ('true', '1', 'yes'):
        print_error("FLASK_DEBUG is enabled - MUST be disabled in production")
        all_valid = False
    else:
        print_success("FLASK_DEBUG is disabled")

    # Check DEV_AUTH_BYPASS
    dev_auth = os.getenv('DEV_AUTH_BYPASS')
    if dev_auth and dev_auth.lower() in ('true', '1', 'yes'):
        print_error("DEV_AUTH_BYPASS is enabled - MUST be disabled in production")
        all_valid = False
    else:
        print_success("DEV_AUTH_BYPASS is disabled")

    # Check secret key strength
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if secret_key:
        if len(secret_key) >= 64:
            print_success(f"FLASK_SECRET_KEY is strong ({len(secret_key)} characters)")
        elif len(secret_key) >= 32:
            print_success(f"FLASK_SECRET_KEY is adequate ({len(secret_key)} characters)")
        else:
            print_warning(f"FLASK_SECRET_KEY is weak ({len(secret_key)} characters)")

    return all_valid


def check_dependencies():
    """Verify all dependencies are installed"""
    print_header("Checking Dependencies")

    requirements_file = backend_dir / 'requirements.txt'

    if not requirements_file.exists():
        print_error(f"requirements.txt not found at {requirements_file}")
        return False

    try:
        import pkg_resources
        with open(requirements_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        missing = []
        for requirement in requirements:
            try:
                pkg_name = requirement.split('==')[0].split('>=')[0].split('<=')[0]
                pkg_resources.require(pkg_name)
            except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
                missing.append(requirement)

        if missing:
            print_warning(f"{len(missing)} dependencies may need installation:")
            for req in missing[:5]:  # Show first 5
                print(f"  - {req}")
            print("  Run: pip install -r requirements.txt")
            return False
        else:
            print_success(f"All {len(requirements)} backend dependencies installed")
            return True

    except Exception as e:
        print_warning(f"Could not verify dependencies: {e}")
        return True  # Don't fail


def main():
    """Run all pre-deployment checks"""
    print(f"\n{Colors.BLUE}")
    print("=" * 60)
    print("RoomieRoster Pre-Deployment Validation")
    print("=" * 60)
    print(f"{Colors.END}")

    checks = {
        'Environment Variables': check_environment_variables(),
        'Database Connection': check_database_connection(),
        'Migration Status': check_migrations(),
        'Frontend Build': check_frontend_build(),
        'Security Configuration': check_security_configuration(),
        'Dependencies': check_dependencies()
    }

    # Summary
    print_header("Validation Summary")

    passed = sum(1 for result in checks.values() if result)
    total = len(checks)

    for check_name, result in checks.items():
        if result:
            print_success(f"{check_name}")
        else:
            print_error(f"{check_name}")

    print(f"\n{passed}/{total} checks passed")

    if passed == total:
        print(f"\n{Colors.GREEN}✅ ALL CHECKS PASSED - Ready for deployment{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}❌ DEPLOYMENT VALIDATION FAILED{Colors.END}")
        print(f"{Colors.RED}Fix the issues above before deploying{Colors.END}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
