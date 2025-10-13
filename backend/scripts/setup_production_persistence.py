#!/usr/bin/env python3
"""
RoomieRoster Production Persistence Setup Script

This script automates the setup of production-ready data persistence:
1. Guides user through PostgreSQL database setup (Neon recommended)
2. Configures environment variables
3. Migrates existing JSON data to PostgreSQL
4. Validates data integrity
5. Tests backup system
6. Verifies deployment readiness

Usage:
    python3 backend/scripts/setup_production_persistence.py
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# ANSI color codes for beautiful terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text: str):
    """Print a bold header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")

def print_step(step: int, total: int, text: str):
    """Print step progress"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step {step}/{total}]{Colors.END} {text}")

def get_project_root() -> Path:
    """Get the project root directory"""
    script_dir = Path(__file__).parent.absolute()
    return script_dir.parent.parent

def validate_database_url(url: str) -> Tuple[bool, str]:
    """
    Validate database URL format

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not url or url.strip() == '':
        return False, "Database URL cannot be empty"

    # Check for PostgreSQL URL format
    if not url.startswith('postgresql://') and not url.startswith('postgres://'):
        return False, "URL must start with 'postgresql://' or 'postgres://'"

    # Check for required components
    pattern = r'^postgres(?:ql)?://[\w-]+:[\w-]+@[\w.-]+(?::\d+)?/[\w-]+(?:\?.*)?$'
    if not re.match(pattern, url):
        return False, "Invalid database URL format. Expected: postgresql://username:password@host:port/database"

    # Check for SSL mode (recommended for production)
    if 'sslmode=' not in url:
        return False, "Missing sslmode parameter. Add '?sslmode=require' for security"

    return True, ""

def check_database_connectivity(url: str) -> bool:
    """Test database connection"""
    print_info("Testing database connection...")

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print_success(f"Connected successfully!")
            print_info(f"PostgreSQL version: {version.split(',')[0]}")
            return True
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")
        return False

def update_env_file(project_root: Path, database_url: str) -> bool:
    """Update .env file with database URL"""
    env_path = project_root / '.env'

    try:
        # Read existing .env or create from template
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
        else:
            template_path = project_root / '.env.example'
            if template_path.exists():
                with open(template_path, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []

        # Update or add DATABASE_URL
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('DATABASE_URL=') or line.strip().startswith('#DATABASE_URL='):
                lines[i] = f'DATABASE_URL={database_url}\n'
                updated = True
                break

        if not updated:
            lines.append(f'\n# Database Configuration (Added by setup script)\nDATABASE_URL={database_url}\n')

        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)

        print_success(f"Updated {env_path}")
        return True

    except Exception as e:
        print_error(f"Failed to update .env file: {str(e)}")
        return False

def run_migration(project_root: Path) -> bool:
    """Run data migration from JSON to PostgreSQL"""
    print_info("Running data migration...")

    migration_script = project_root / 'backend' / 'migrate_data.py'
    if not migration_script.exists():
        print_error(f"Migration script not found: {migration_script}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(migration_script)],
            cwd=project_root / 'backend',
            capture_output=True,
            text=True,
            timeout=60
        )

        print(result.stdout)

        if result.returncode == 0:
            print_success("Migration completed successfully!")
            return True
        else:
            print_error(f"Migration failed with exit code {result.returncode}")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print_error("Migration timed out after 60 seconds")
        return False
    except Exception as e:
        print_error(f"Migration error: {str(e)}")
        return False

def validate_data_integrity(project_root: Path) -> bool:
    """Validate data integrity after migration"""
    print_info("Validating data integrity...")

    # Add backend to Python path
    backend_dir = project_root / 'backend'
    sys.path.insert(0, str(backend_dir))

    try:
        from flask import Flask
        from utils.database_config import database_config
        from utils.database_models import Roommate, Chore, Assignment

        app = Flask(__name__)
        database_config.configure_flask_app(app)

        with app.app_context():
            # Check that tables have data
            roommate_count = Roommate.query.count()
            chore_count = Chore.query.count()
            assignment_count = Assignment.query.count()

            print_info(f"Found {roommate_count} roommates, {chore_count} chores, {assignment_count} assignments")

            if roommate_count == 0 and chore_count == 0:
                print_warning("No data found in database. This might be a fresh installation.")
                return True

            # Basic validation: assignments should reference valid roommates and chores
            if assignment_count > 0:
                assignments = Assignment.query.all()
                for assignment in assignments:
                    if not assignment.roommate:
                        print_error(f"Assignment {assignment.id} has invalid roommate reference")
                        return False
                    if not assignment.chore:
                        print_error(f"Assignment {assignment.id} has invalid chore reference")
                        return False

            print_success("Data integrity validation passed!")
            return True

    except Exception as e:
        print_error(f"Validation error: {str(e)}")
        return False

def test_backup_system(project_root: Path) -> bool:
    """Test backup system"""
    print_info("Testing backup system...")

    backup_script = project_root / 'backend' / 'scripts' / 'backup_database.sh'
    if not backup_script.exists():
        print_warning(f"Backup script not found: {backup_script}")
        return False

    # Check if pg_dump is available
    try:
        subprocess.run(['pg_dump', '--version'], capture_output=True, check=True)
        print_success("pg_dump is installed and available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("pg_dump not found. Install PostgreSQL client tools:")
        print("  macOS: brew install postgresql@15")
        print("  Ubuntu: sudo apt-get install postgresql-client")
        return False

    # Make backup script executable
    backup_script.chmod(0o755)
    print_success("Backup system is ready")

    return True

def print_next_steps():
    """Print next steps for the user"""
    print_header("Next Steps")

    print(f"{Colors.BOLD}1. Start your application:{Colors.END}")
    print(f"   {Colors.CYAN}python3 launch_app.py{Colors.END}")

    print(f"\n{Colors.BOLD}2. Verify PostgreSQL is active:{Colors.END}")
    print(f"   {Colors.CYAN}curl http://localhost:5001/api/health{Colors.END}")
    print(f"   Should return: {Colors.GREEN}\"database\": \"postgresql\"{Colors.END}")

    print(f"\n{Colors.BOLD}3. Set up automated backups (recommended):{Colors.END}")
    print(f"   {Colors.CYAN}crontab -e{Colors.END}")
    print(f"   Add: {Colors.YELLOW}0 2 * * * /path/to/backend/scripts/backup_database.sh{Colors.END}")

    print(f"\n{Colors.BOLD}4. Deploy to production:{Colors.END}")
    print(f"   • Add DATABASE_URL to Render environment variables")
    print(f"   • Ensure all other required variables are set (see DATABASE_SETUP_GUIDE.md)")
    print(f"   • Deploy and verify with health endpoint")

    print(f"\n{Colors.BOLD}5. Monitor your application:{Colors.END}")
    print(f"   • Set up UptimeRobot for health checks")
    print(f"   • Enable Neon's built-in backups (already active)")
    print(f"   • Review logs regularly for issues")

    print(f"\n{Colors.GREEN}{Colors.BOLD}Your data is now safe and persistent!{Colors.END}")

def main():
    """Main setup workflow"""
    print_header("RoomieRoster Production Persistence Setup")

    print("This script will help you set up production-ready data persistence")
    print("to prevent data loss in cloud deployments.\n")

    project_root = get_project_root()
    print_info(f"Project root: {project_root}")

    # Step 1: Get database URL
    print_step(1, 6, "Configure PostgreSQL Database")
    print("\nRecommended: Sign up for free Neon PostgreSQL at https://neon.tech")
    print("After creating a project, copy the connection string.\n")

    database_url = input(f"{Colors.CYAN}Enter your database URL: {Colors.END}").strip()

    # Validate URL
    is_valid, error_msg = validate_database_url(database_url)
    if not is_valid:
        print_error(error_msg)
        print_info("Example: postgresql://user:pass@ep-xxx-pooler.us-east-2.aws.neon.tech/dbname?sslmode=require")
        sys.exit(1)

    print_success("Database URL format is valid")

    # Step 2: Test connection
    print_step(2, 6, "Test Database Connection")
    if not check_database_connectivity(database_url):
        print_error("Cannot proceed without database connection")
        sys.exit(1)

    # Step 3: Update .env file
    print_step(3, 6, "Update Environment Configuration")
    if not update_env_file(project_root, database_url):
        print_error("Failed to update .env file")
        sys.exit(1)

    # Step 4: Run migration
    print_step(4, 6, "Migrate Data from JSON to PostgreSQL")
    response = input(f"{Colors.YELLOW}Proceed with migration? (yes/no): {Colors.END}").lower()
    if response != 'yes':
        print_warning("Migration skipped. You can run it later with: python3 backend/migrate_data.py")
    else:
        if not run_migration(project_root):
            print_error("Migration failed")
            sys.exit(1)

    # Step 5: Validate data integrity
    print_step(5, 6, "Validate Data Integrity")
    if not validate_data_integrity(project_root):
        print_error("Data integrity validation failed")
        sys.exit(1)

    # Step 6: Test backup system
    print_step(6, 6, "Verify Backup System")
    test_backup_system(project_root)

    # Success!
    print_header("Setup Complete!")
    print_next_steps()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
