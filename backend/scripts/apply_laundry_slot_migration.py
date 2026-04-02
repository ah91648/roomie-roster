#!/usr/bin/env python3
"""
Manually apply the laundry_slot_id migration to pomodoro_sessions table.
This script adds the laundry_slot_id column to an existing database.
"""

import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from utils.database_config import db, database_config
from flask import Flask

def create_app():
    """Create Flask app for database context"""
    app = Flask(__name__)

    # Configure database
    db_url = database_config.get_database_url()
    if not db_url:
        print("❌ DATABASE_URL not configured")
        sys.exit(1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    return app

def apply_migration(app):
    """Apply the laundry_slot_id migration"""
    with app.app_context():
        try:
            # Check if column already exists
            check_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='pomodoro_sessions'
                AND column_name='laundry_slot_id'
            """)

            result = db.session.execute(check_query).fetchone()

            if result:
                print("✅ Column laundry_slot_id already exists in pomodoro_sessions table")
                return True

            print("🚀 Adding laundry_slot_id column to pomodoro_sessions table...")

            # Add the column
            add_column_query = text("""
                ALTER TABLE pomodoro_sessions
                ADD COLUMN laundry_slot_id INTEGER
            """)
            db.session.execute(add_column_query)

            # Add foreign key constraint
            add_fk_query = text("""
                ALTER TABLE pomodoro_sessions
                ADD CONSTRAINT fk_pomodoro_sessions_laundry_slot_id
                FOREIGN KEY (laundry_slot_id) REFERENCES laundry_slots(id)
            """)
            db.session.execute(add_fk_query)

            # Add index
            add_index_query = text("""
                CREATE INDEX idx_pomodoro_laundry_slot
                ON pomodoro_sessions(laundry_slot_id)
            """)
            db.session.execute(add_index_query)

            db.session.commit()

            print("✅ Migration applied successfully!")
            print("   - Added column: laundry_slot_id")
            print("   - Added foreign key: fk_pomodoro_sessions_laundry_slot_id")
            print("   - Added index: idx_pomodoro_laundry_slot")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            return False

def main():
    print("=" * 60)
    print("Laundry Slot Pomodoro Migration Script")
    print("=" * 60)

    app = create_app()

    if apply_migration(app):
        print("=" * 60)
        print("✅ Migration completed successfully")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ Migration failed")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    main()
