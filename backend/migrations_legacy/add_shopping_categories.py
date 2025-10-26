"""
Migration script to add shopping categories feature.

This migration adds:
1. category column to shopping_items table (PostgreSQL)
2. shopping_categories column to application_state table (PostgreSQL)
3. category field to shopping_list.json items (JSON fallback)
4. shopping_categories list to state.json (JSON fallback)

Usage:
    python migrations/add_shopping_categories.py
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from utils.database_config import db, database_config
from sqlalchemy import text, inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_postgresql(app):
    """Migrate PostgreSQL database to add category support."""
    with app.app_context():
        logger.info("Starting PostgreSQL migration...")

        try:
            inspector = inspect(db.engine)

            # Check if category column already exists in shopping_items
            shopping_columns = [col['name'] for col in inspector.get_columns('shopping_items')]
            if 'category' not in shopping_columns:
                logger.info("Adding 'category' column to shopping_items table...")
                db.session.execute(text(
                    "ALTER TABLE shopping_items ADD COLUMN category VARCHAR(100) DEFAULT 'General' NOT NULL"
                ))
                logger.info("✓ Added category column to shopping_items")
            else:
                logger.info("✓ Category column already exists in shopping_items")

            # Check if shopping_categories column exists in application_state
            state_columns = [col['name'] for col in inspector.get_columns('application_state')]
            if 'shopping_categories' not in state_columns:
                logger.info("Adding 'shopping_categories' column to application_state table...")
                db.session.execute(text(
                    "ALTER TABLE application_state ADD COLUMN shopping_categories JSON DEFAULT '[]'::json"
                ))
                logger.info("✓ Added shopping_categories column to application_state")
            else:
                logger.info("✓ Shopping_categories column already exists in application_state")

            # Initialize default category if empty
            result = db.session.execute(text(
                "SELECT shopping_categories FROM application_state LIMIT 1"
            )).first()

            if result and (not result[0] or result[0] == '[]' or len(result[0]) == 0):
                logger.info("Initializing default 'General' category...")
                db.session.execute(text(
                    "UPDATE application_state SET shopping_categories = :categories",
                ), {'categories': json.dumps(['General'])})
                logger.info("✓ Initialized default category")

            # Commit all changes
            db.session.commit()
            logger.info("✓ PostgreSQL migration completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Error during PostgreSQL migration: {e}")
            db.session.rollback()
            raise

def migrate_json_files(data_dir='data'):
    """Migrate JSON files to add category support."""
    logger.info("Starting JSON files migration...")
    data_path = Path(data_dir)

    try:
        # Migrate shopping_list.json
        shopping_list_file = data_path / 'shopping_list.json'
        if shopping_list_file.exists():
            with open(shopping_list_file, 'r') as f:
                shopping_list = json.load(f)

            # Add category field to all items
            modified = False
            for item in shopping_list:
                if 'category' not in item:
                    item['category'] = 'General'
                    modified = True

            if modified:
                # Backup original file
                backup_file = data_path / f'shopping_list.json.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                with open(backup_file, 'w') as f:
                    json.dump(shopping_list, f, indent=2)
                logger.info(f"✓ Created backup: {backup_file}")

                # Write updated file
                with open(shopping_list_file, 'w') as f:
                    json.dump(shopping_list, f, indent=2)
                logger.info(f"✓ Added category field to {len(shopping_list)} shopping items")
            else:
                logger.info("✓ Shopping items already have category field")
        else:
            logger.info("✓ No shopping_list.json found (will be created on first use)")

        # Migrate state.json
        state_file = data_path / 'state.json'
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)

            if 'shopping_categories' not in state:
                # Backup original file
                backup_file = data_path / f'state.json.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                with open(backup_file, 'w') as f:
                    json.dump(state, f, indent=2)
                logger.info(f"✓ Created backup: {backup_file}")

                # Add shopping_categories field
                state['shopping_categories'] = ['General']

                # Write updated file
                with open(state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                logger.info("✓ Added shopping_categories to state.json")
            else:
                logger.info("✓ State.json already has shopping_categories field")
        else:
            logger.info("✓ No state.json found (will be created on first use)")

        logger.info("✓ JSON files migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error during JSON files migration: {e}")
        raise

def main():
    """Main migration entry point."""
    logger.info("=" * 60)
    logger.info("Shopping Categories Migration")
    logger.info("=" * 60)

    # Create Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_config.get_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    use_database = database_config.should_use_database()

    try:
        if use_database:
            logger.info("Database configured - migrating PostgreSQL")
            migrate_postgresql(app)
        else:
            logger.info("No database configured - migrating JSON files")

        # Always migrate JSON files as fallback/backup
        migrate_json_files()

        logger.info("=" * 60)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Restart your application")
        logger.info("2. Test category functionality")
        logger.info("3. Create custom categories via the UI or API")

    except Exception as e:
        logger.error("=" * 60)
        logger.error("✗ Migration failed!")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
