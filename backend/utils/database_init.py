"""
Database initialization and management utilities for RoomieRoster application.
Handles table creation, initial setup, and database health checks.
"""

import logging
from typing import Dict, Any, Optional
from flask import Flask
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from .database_config import db, database_config
from .database_models import (
    Roommate, Chore, SubChore, Assignment, ApplicationState,
    ShoppingItem, Request, LaundrySlot, BlockedTimeSlot
)

class DatabaseInitializer:
    """Handles database initialization and setup operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def initialize_database(self, app: Flask) -> bool:
        """
        Initialize the database with tables and initial state.
        
        Args:
            app: Flask application instance
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not database_config.should_use_database():
            self.logger.info("Database not configured, skipping initialization")
            return True
        
        try:
            with app.app_context():
                # Create all tables
                self.logger.info("Creating database tables...")
                db.create_all()
                self.logger.info("Database tables created successfully")
                
                # Initialize application state if it doesn't exist
                self._initialize_application_state()
                
                # Verify database connectivity
                if self._verify_database_connection():
                    self.logger.info("Database initialization completed successfully")
                    return True
                else:
                    self.logger.error("Database connectivity verification failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False
    
    def _initialize_application_state(self):
        """Initialize the application state table with default values."""
        try:
            # Check if application state already exists
            state = ApplicationState.query.first()
            if state is None:
                # Create initial application state
                initial_state = ApplicationState(
                    last_run_date=None,
                    predefined_chore_states={},
                    global_predefined_rotation=0
                )
                db.session.add(initial_state)
                db.session.commit()
                self.logger.info("Initial application state created")
            else:
                self.logger.info("Application state already exists")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize application state: {e}")
            db.session.rollback()
            raise
    
    def _verify_database_connection(self) -> bool:
        """
        Verify database connectivity by performing a simple query.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Try to query the application state table
            result = db.session.execute(text("SELECT 1")).scalar()
            return result == 1
        except Exception as e:
            self.logger.error(f"Database connectivity check failed: {e}")
            return False
    
    def get_database_status(self) -> Dict[str, Any]:
        """
        Get comprehensive database status information.
        
        Returns:
            Dict[str, Any]: Database status information
        """
        status = {
            'database_configured': database_config.should_use_database(),
            'connection_healthy': False,
            'tables_exist': False,
            'table_counts': {},
            'storage_type': 'PostgreSQL' if database_config.should_use_database() else 'JSON Files'
        }
        
        if not database_config.should_use_database():
            status['connection_healthy'] = True  # JSON files don't need connection
            return status
        
        try:
            # Check connection health
            status['connection_healthy'] = self._verify_database_connection()
            
            if status['connection_healthy']:
                # Check if tables exist and get counts
                status['tables_exist'] = self._check_tables_exist()
                if status['tables_exist']:
                    status['table_counts'] = self._get_table_counts()
                    
        except Exception as e:
            self.logger.error(f"Error getting database status: {e}")
            status['error'] = str(e)
        
        return status
    
    def _check_tables_exist(self) -> bool:
        """
        Check if all required tables exist in the database.
        
        Returns:
            bool: True if all tables exist, False otherwise
        """
        try:
            required_tables = [
                'roommates', 'chores', 'sub_chores', 'assignments',
                'application_state', 'shopping_items', 'requests',
                'laundry_slots', 'blocked_time_slots'
            ]
            
            for table_name in required_tables:
                result = db.session.execute(
                    text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
                ).scalar()
                if not result:
                    self.logger.warning(f"Table {table_name} does not exist")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking table existence: {e}")
            return False
    
    def _get_table_counts(self) -> Dict[str, int]:
        """
        Get record counts for all tables.
        
        Returns:
            Dict[str, int]: Table name to record count mapping
        """
        counts = {}
        try:
            models = [
                ('roommates', Roommate),
                ('chores', Chore),
                ('sub_chores', SubChore),
                ('assignments', Assignment),
                ('application_state', ApplicationState),
                ('shopping_items', ShoppingItem),
                ('requests', Request),
                ('laundry_slots', LaundrySlot),
                ('blocked_time_slots', BlockedTimeSlot)
            ]
            
            for table_name, model_class in models:
                count = model_class.query.count()
                counts[table_name] = count
                
        except Exception as e:
            self.logger.error(f"Error getting table counts: {e}")
        
        return counts
    
    def reset_database(self, app: Flask) -> bool:
        """
        Reset the database by dropping and recreating all tables.
        WARNING: This will delete all data!
        
        Args:
            app: Flask application instance
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not database_config.should_use_database():
            self.logger.warning("Cannot reset database - not using database storage")
            return False
        
        try:
            with app.app_context():
                self.logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST!")
                
                # Drop all tables
                db.drop_all()
                self.logger.info("All tables dropped")
                
                # Recreate all tables
                db.create_all()
                self.logger.info("All tables recreated")
                
                # Initialize application state
                self._initialize_application_state()
                
                self.logger.info("Database reset completed successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Database reset failed: {e}")
            return False

# Global database initializer instance
database_initializer = DatabaseInitializer()