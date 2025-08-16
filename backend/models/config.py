"""
Database configuration for SQLAlchemy models.

This module provides configuration classes for different environments
(development, testing, production) and database setup utilities.
"""

import os
from pathlib import Path


class DatabaseConfig:
    """Base database configuration."""
    
    # Flask-SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20
    }


class DevelopmentConfig(DatabaseConfig):
    """Development database configuration."""
    
    DEBUG = True
    
    # Use SQLite for development
    BASE_DIR = Path(__file__).parent.parent
    DATABASE_PATH = BASE_DIR / 'data' / 'roomieroster.db'
    
    # Ensure data directory exists
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    
    # Development-specific settings
    SQLALCHEMY_ECHO = True  # Log SQL queries in development


class TestingConfig(DatabaseConfig):
    """Testing database configuration."""
    
    TESTING = True
    DEBUG = True
    
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Testing-specific settings
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(DatabaseConfig):
    """Production database configuration."""
    
    DEBUG = False
    
    # Use environment variable for production database URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    if not SQLALCHEMY_DATABASE_URI:
        # Fallback to SQLite if no DATABASE_URL is set
        BASE_DIR = Path(__file__).parent.parent
        DATABASE_PATH = BASE_DIR / 'data' / 'roomieroster_prod.db'
        DATABASE_PATH.parent.mkdir(exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    
    # Handle PostgreSQL URL format for Render/Heroku
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # Production-specific settings
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_size': 5,
        'max_overflow': 10
    }


# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}


def get_config(config_name=None):
    """Get configuration class based on environment."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config_by_name.get(config_name, DevelopmentConfig)


def setup_database(app, config_name=None):
    """Set up database configuration for Flask app."""
    config = get_config(config_name)
    
    # Apply configuration
    for key, value in config.__dict__.items():
        if not key.startswith('_'):
            app.config[key] = value
    
    # Initialize SQLAlchemy with app
    from .models import db
    db.init_app(app)
    
    return db


def create_database_tables(app):
    """Create all database tables."""
    from .models import db, create_all_tables
    create_all_tables(app)


def reset_database(app):
    """Reset database by dropping and recreating all tables."""
    from .models import db, reset_database as reset_db
    reset_db(app)


# Database utility functions
def get_database_info(app):
    """Get information about the current database configuration."""
    with app.app_context():
        from .models import db
        
        # Get engine info
        engine = db.engine
        database_url = str(engine.url)
        
        # Hide password in URL for security
        if '@' in database_url:
            parts = database_url.split('@')
            if ':' in parts[0]:
                user_pass = parts[0].split(':')
                if len(user_pass) > 2:  # Has password
                    user_pass[-1] = '***'
                    parts[0] = ':'.join(user_pass)
                    database_url = '@'.join(parts)
        
        # Get table info
        inspector = db.inspect(engine)
        table_names = inspector.get_table_names()
        
        return {
            'database_url': database_url,
            'database_type': engine.dialect.name,
            'table_count': len(table_names),
            'tables': table_names
        }


def check_database_connection(app):
    """Check if database connection is working."""
    try:
        with app.app_context():
            from .models import db
            
            # Try to execute a simple query
            result = db.engine.execute('SELECT 1')
            result.close()
            
            return True, "Database connection successful"
    
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


def backup_database(app, backup_path=None):
    """Create a backup of the database (SQLite only)."""
    try:
        with app.app_context():
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if not database_url.startswith('sqlite:///'):
                return False, "Backup is only supported for SQLite databases"
            
            # Extract database file path
            db_path = database_url.replace('sqlite:///', '')
            db_file = Path(db_path)
            
            if not db_file.exists():
                return False, f"Database file not found: {db_path}"
            
            # Create backup
            if backup_path is None:
                backup_dir = db_file.parent / 'backups'
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f"roomieroster_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            import shutil
            shutil.copy2(db_file, backup_path)
            
            return True, f"Database backed up to: {backup_path}"
    
    except Exception as e:
        return False, f"Backup failed: {str(e)}"


def restore_database(app, backup_path):
    """Restore database from backup (SQLite only)."""
    try:
        with app.app_context():
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if not database_url.startswith('sqlite:///'):
                return False, "Restore is only supported for SQLite databases"
            
            # Extract database file path
            db_path = database_url.replace('sqlite:///', '')
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                return False, f"Backup file not found: {backup_path}"
            
            # Close existing connections
            from .models import db
            db.session.close()
            db.engine.dispose()
            
            # Restore database
            import shutil
            shutil.copy2(backup_file, db_path)
            
            return True, f"Database restored from: {backup_path}"
    
    except Exception as e:
        return False, f"Restore failed: {str(e)}"


if __name__ == "__main__":
    # Quick test of configuration
    for env in ['development', 'testing', 'production']:
        config = get_config(env)
        print(f"{env.title()} Config:")
        print(f"  Database URI: {config.SQLALCHEMY_DATABASE_URI}")
        print(f"  Debug: {getattr(config, 'DEBUG', False)}")
        print(f"  Echo SQL: {getattr(config, 'SQLALCHEMY_ECHO', False)}")
        print()