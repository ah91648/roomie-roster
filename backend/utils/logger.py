"""
Structured JSON logging configuration for RoomieRoster.

This module provides production-ready logging with:
- JSON-formatted logs for easy parsing
- Correlation IDs for request tracing
- Automatic log level configuration per environment
- Request/response logging middleware
- Sensitive data sanitization

Usage:
    from utils.logger import configure_logging, get_logger

    # In app.py:
    configure_logging(app)

    # In any module:
    logger = get_logger(__name__)
    logger.info("User logged in", extra={'user_id': 123})
"""

import logging
import json
import sys
import os
import uuid
from datetime import datetime
from flask import request, g, has_request_context
from functools import wraps


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs logs as JSON for easier parsing by log aggregation tools.
    """

    SENSITIVE_KEYS = {'password', 'secret', 'token', 'api_key', 'authorization'}

    def format(self, record):
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add request context if available
        if has_request_context():
            log_data['request'] = {
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'correlation_id': getattr(g, 'correlation_id', None),
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }

        # Add extra fields from record
        if hasattr(record, 'extra_data'):
            sanitized_extra = self._sanitize_data(record.extra_data)
            log_data.update(sanitized_extra)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_data)

    def _sanitize_data(self, data):
        """Remove sensitive information from log data"""
        if isinstance(data, dict):
            return {
                k: '***REDACTED***' if k.lower() in self.SENSITIVE_KEYS else
                   self._sanitize_data(v) if isinstance(v, (dict, list)) else v
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        return data


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development.

    Provides colored output and easy-to-read format for local development.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        # Add correlation ID if available
        if has_request_context() and hasattr(g, 'correlation_id'):
            record.correlation_id = g.correlation_id
        else:
            record.correlation_id = ''

        return super().format(record)


def configure_logging(app):
    """
    Configure application logging based on environment.

    Args:
        app: Flask application instance
    """
    flask_env = os.getenv('FLASK_ENV', 'production')
    is_production = flask_env == 'production'

    # Remove existing handlers
    app.logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter based on environment
    if is_production:
        # JSON logs for production (easier to parse)
        formatter = JSONFormatter()
        log_level = logging.INFO
        app.logger.info("Configuring JSON logging for production")
    else:
        # Human-readable logs for development
        formatter = HumanReadableFormatter(
            fmt='%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        log_level = logging.DEBUG
        print("Configuring human-readable logging for development")

    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    # Configure app logger
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    app.logger.info(f"Logging configured for {flask_env} environment")


def get_logger(name):
    """
    Get a logger instance with structured logging support.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def add_correlation_id():
    """
    Add correlation ID to request context for tracing.

    Should be called at the beginning of each request.
    """
    if not has_request_context():
        return

    # Generate or extract correlation ID
    correlation_id = request.headers.get('X-Correlation-ID')
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    g.correlation_id = correlation_id


def request_logging_middleware(app):
    """
    Add request/response logging middleware to Flask app.

    Logs all incoming requests and outgoing responses with timing information.

    Args:
        app: Flask application instance
    """
    logger = get_logger('request_logger')

    @app.before_request
    def log_request():
        """Log incoming request"""
        add_correlation_id()

        # Store request start time
        g.request_start_time = datetime.utcnow()

        # Don't log health checks in production (too noisy)
        if request.path == '/api/health' and os.getenv('FLASK_ENV') == 'production':
            return

        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'extra_data': {
                    'method': request.method,
                    'path': request.path,
                    'correlation_id': g.correlation_id,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent')
                }
            }
        )

    @app.after_request
    def log_response(response):
        """Log outgoing response"""
        # Skip health checks in production
        if request.path == '/api/health' and os.getenv('FLASK_ENV') == 'production':
            return response

        # Calculate request duration
        if hasattr(g, 'request_start_time'):
            duration_ms = (datetime.utcnow() - g.request_start_time).total_seconds() * 1000
        else:
            duration_ms = 0

        log_level = logging.INFO if response.status_code < 400 else logging.WARNING

        logger.log(
            log_level,
            f"Request completed: {request.method} {request.path} - {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                'extra_data': {
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                    'correlation_id': getattr(g, 'correlation_id', None)
                }
            }
        )

        # Add correlation ID to response headers
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id

        return response

    @app.errorhandler(Exception)
    def log_exception(error):
        """Log uncaught exceptions"""
        logger.error(
            f"Unhandled exception: {str(error)}",
            exc_info=True,
            extra={
                'extra_data': {
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    'correlation_id': getattr(g, 'correlation_id', None),
                    'path': request.path if has_request_context() else None
                }
            }
        )

        # Re-raise to allow other error handlers to process
        raise


def log_with_context(logger_func):
    """
    Decorator to add context to log calls.

    Usage:
        @log_with_context
        def my_function():
            logger.info("Something happened", user_id=123, action="create")
    """
    @wraps(logger_func)
    def wrapper(message, **kwargs):
        if kwargs:
            return logger_func(message, extra={'extra_data': kwargs})
        return logger_func(message)
    return wrapper


# Example usage in routes:
# from utils.logger import get_logger
# logger = get_logger(__name__)
#
# @app.route('/api/example')
# def example():
#     logger.info("Processing request", user_id=123, action="view")
#     # ... route logic ...
