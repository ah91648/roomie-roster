"""
Database configuration and connection management for RoomieRoster application.
Supports both development (JSON files) and production (PostgreSQL) environments.
"""

import os
import logging
from typing import Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Initialize SQLAlchemy instance
db = SQLAlchemy()

class DatabaseConfig:
    """Database configuration manager for RoomieRoster application."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._engine = None
        self._use_database = None
        
    def get_database_url(self) -> Optional[str]:
        """
        Get the database URL from environment variables.
        
        Returns:
            Optional[str]: Database URL if configured, None otherwise
        """
        # Check for Neon PostgreSQL connection string
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return database_url
            
        # Check for individual connection parameters
        host = os.getenv('DATABASE_HOST')
        port = os.getenv('DATABASE_PORT', '5432')
        database = os.getenv('DATABASE_NAME')
        username = os.getenv('DATABASE_USER')
        password = os.getenv('DATABASE_PASSWORD')
        
        if all([host, database, username, password]):
            return f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require"
        
        return None
    
    def should_use_database(self) -> bool:
        """
        Determine if the application should use a database or JSON files.
        
        Returns:
            bool: True if database should be used, False for JSON files
        """
        if self._use_database is not None:
            return self._use_database
            
        # Check if database URL is available
        database_url = self.get_database_url()
        if not database_url:
            self.logger.info("No database URL found, using JSON file storage")
            self._use_database = False
            return False
        
        # Test database connection
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            self.logger.info("Database connection successful, using PostgreSQL storage")
            self._use_database = True
            return True
        except OperationalError as e:
            self.logger.warning(f"Database connection failed: {e}")
            self.logger.info("Falling back to JSON file storage")
            self._use_database = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected database error: {e}")
            self._use_database = False
            return False
    
    def configure_flask_app(self, app):
        """
        Configure Flask app with database settings.
        
        Args:
            app: Flask application instance
        """
        if self.should_use_database():
            database_url = self.get_database_url()
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_pre_ping': True,
                'pool_recycle': 300,
                'connect_args': {
                    'sslmode': 'require',
                    'connect_timeout': 10
                }
            }
            
            # Initialize SQLAlchemy with app
            db.init_app(app)
            
            self.logger.info("Flask app configured for PostgreSQL database")
        else:
            self.logger.info("Flask app configured for JSON file storage")
    
    def create_tables(self, app):
        """
        Create database tables if using database storage.
        
        Args:
            app: Flask application instance
        """
        if not self.should_use_database():
            return
            
        try:
            with app.app_context():
                # Import models to ensure they're registered
                from .database_models import (
                    Roommate, Chore, SubChore, Assignment, 
                    ShoppingItem, Request, LaundrySlot, BlockedTimeSlot
                )
                
                # Create all tables
                db.create_all()
                self.logger.info("Database tables created successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_database_info(self) -> dict:
        """
        Get information about the current database configuration.
        
        Returns:
            dict: Database configuration information
        """
        return {
            'using_database': self.should_use_database(),
            'database_url_configured': self.get_database_url() is not None,
            'storage_type': 'PostgreSQL' if self.should_use_database() else 'JSON Files'
        }

# Global database configuration instance
database_config = DatabaseConfig()