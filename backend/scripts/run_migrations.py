#!/usr/bin/env python3
"""
Migration runner script for RoomieRoster deployment.

This script safely applies database migrations with proper validation and error handling.
Used in production deployments to ensure database schema is up-to-date.

Usage:
    python scripts/run_migrations.py [--dry-run]
"""

import sys
import os
import logging
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from flask import Flask
from flask_migrate import Migrate, upgrade, current as get_current
from utils.database_config import db, database_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create Flask app for migration context"""
    app = Flask(__name__)

    # Configure database
    db_url = database_config.get_database_url()
    if not db_url:
        logger.error("❌ DATABASE_URL not configured")
        logger.error("Set DATABASE_URL environment variable before running migrations")
        sys.exit(1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Flask-Migrate
    db.init_app(app)
    migrations_dir = backend_dir / 'migrations'
    Migrate(app, db, directory=str(migrations_dir))

    return app


def check_database_connectivity(app):
    """Verify database is accessible"""
    with app.app_context():
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False


def get_migration_status(app):
    """Get current migration status"""
    with app.app_context():
        try:
            current_rev = get_current()
            if current_rev:
                logger.info(f"📊 Current migration revision: {current_rev}")
            else:
                logger.info("📊 No migrations applied yet")
            return current_rev
        except Exception as e:
            logger.warning(f"⚠️  Could not determine migration status: {e}")
            return None


def run_migrations(app, dry_run=False):
    """Apply pending migrations"""
    with app.app_context():
        try:
            if dry_run:
                logger.info("🔍 DRY RUN MODE - No changes will be made")
                logger.info("Would run: flask db upgrade")
                return True

            logger.info("🚀 Applying migrations...")
            upgrade()
            logger.info("✅ Migrations applied successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            logger.error("Database may be in an inconsistent state")
            logger.error("Consider running: flask db downgrade to revert")
            return False


def main():
    """Main migration runner"""
    dry_run = '--dry-run' in sys.argv

    logger.info("=" * 60)
    logger.info("RoomieRoster Database Migration Runner")
    logger.info("=" * 60)

    # Create Flask app
    logger.info("📦 Initializing Flask app...")
    app = create_app()

    # Check database connectivity
    logger.info("🔌 Checking database connectivity...")
    if not check_database_connectivity(app):
        logger.error("Cannot proceed without database connection")
        sys.exit(1)

    # Get current migration status
    logger.info("📋 Checking migration status...")
    get_migration_status(app)

    # Run migrations
    if run_migrations(app, dry_run=dry_run):
        logger.info("=" * 60)
        logger.info("✅ Migration process completed successfully")
        logger.info("=" * 60)

        # Show final status
        get_migration_status(app)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("❌ Migration process failed")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
