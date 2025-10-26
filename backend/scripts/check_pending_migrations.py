#!/usr/bin/env python3
"""
Migration validation script for pre-deployment checks.

This script verifies that all migrations have been applied and warns about pending migrations.
Returns exit code 0 if all migrations applied, exit code 1 if pending migrations exist.

Usage:
    python scripts/check_pending_migrations.py
"""

import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from flask import Flask
from flask_migrate import Migrate
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from utils.database_config import db, database_config


def create_app():
    """Create Flask app for migration context"""
    app = Flask(__name__)

    # Configure database
    db_url = database_config.get_database_url()
    if not db_url:
        print("❌ DATABASE_URL not configured")
        return None

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Flask-Migrate
    db.init_app(app)
    migrations_dir = backend_dir / 'migrations'
    migrate = Migrate(app, db, directory=str(migrations_dir))

    return app, migrate


def check_pending_migrations(app, migrate):
    """Check for pending migrations"""
    with app.app_context():
        try:
            # Get migration script directory
            config = migrate.get_config()
            script = ScriptDirectory.from_config(config)

            # Get current database revision
            with db.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()

            # Get head revision (latest migration)
            head_rev = script.get_current_head()

            print("=" * 60)
            print("Migration Status Check")
            print("=" * 60)
            print(f"📊 Current database revision: {current_rev or 'None (empty database)'}")
            print(f"📊 Latest available revision: {head_rev or 'None (no migrations)'}")

            if current_rev is None and head_rev is not None:
                print("\n⚠️  WARNING: Database has no migrations applied!")
                print(f"Pending migration: {head_rev}")
                print("\nAction required:")
                print("  Run: python scripts/run_migrations.py")
                return False

            if current_rev == head_rev:
                print("\n✅ All migrations applied - database is up-to-date")
                return True

            # Check for pending migrations
            if head_rev is None:
                print("\n⚠️  WARNING: No migration files found")
                return False

            # Get revisions between current and head
            revisions = list(script.iterate_revisions(head_rev, current_rev))

            if revisions:
                print(f"\n⚠️  WARNING: {len(revisions)} pending migration(s) found:")
                for rev in revisions:
                    print(f"  - {rev.revision}: {rev.doc}")

                print("\nAction required:")
                print("  Run: python scripts/run_migrations.py")
                return False

            print("\n✅ All migrations applied")
            return True

        except Exception as e:
            print(f"\n❌ Error checking migrations: {e}")
            return False


def main():
    """Main validation function"""
    result = create_app()
    if result is None:
        sys.exit(1)

    app, migrate = result

    # Check pending migrations
    all_applied = check_pending_migrations(app, migrate)

    print("=" * 60)

    if all_applied:
        print("✅ VALIDATION PASSED: Database schema is up-to-date")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ VALIDATION FAILED: Pending migrations detected")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
