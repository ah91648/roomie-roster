import os
import hashlib
import time
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
from flask import request, jsonify, current_app, session
from typing import Dict, List

class SecurityMiddleware:
    """Enhanced security middleware for RoomieRoster API."""
    
    def __init__(self):
        # Rate limiting storage (in production, use Redis)
        self.rate_limit_storage = defaultdict(list)
        self.blocked_ips = set()
        
        # Security settings
        self.rate_limits = {
            'auth': {'requests': 5, 'window': 300},           # 5 auth attempts per 5 minutes
            'api': {'requests': 100, 'window': 60},           # 100 API calls per minute
            'calendar': {'requests': 20, 'window': 60},       # 20 calendar ops per minute
            'productivity': {'requests': 50, 'window': 60},   # 50 productivity ops per minute
        }
        
        # Security headers
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        }
    
    def init_app(self, app):
        """Initialize security middleware with Flask app."""
        app.security_middleware = self
        
        # Add security headers to all responses
        @app.after_request
        def add_security_headers(response):
            for header, value in self.security_headers.items():
                response.headers[header] = value
            return response
        
        # Clean up old rate limit entries periodically
        self._setup_cleanup_task()
    
    def get_client_ip(self) -> str:
        """Get client IP address, considering proxies."""
        # Check for forwarded headers (be careful in production)
        forwarded_ips = request.headers.getlist("X-Forwarded-For")
        if forwarded_ips:
            return forwarded_ips[0].split(',')[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.remote_addr
    
    def is_rate_limited(self, identifier: str, limit_type: str = 'api') -> bool:
        """Check if identifier is rate limited."""
        if identifier in self.blocked_ips:
            return True
        
        now = time.time()
        limit_config = self.rate_limits.get(limit_type, self.rate_limits['api'])
        window = limit_config['window']
        max_requests = limit_config['requests']
        
        # Clean old entries for this identifier
        self.rate_limit_storage[identifier] = [
            timestamp for timestamp in self.rate_limit_storage[identifier]
            if now - timestamp < window
        ]
        
        # Check if limit exceeded
        if len(self.rate_limit_storage[identifier]) >= max_requests:
            return True
        
        # Record this request
        self.rate_limit_storage[identifier].append(now)
        return False
    
    def block_ip(self, ip: str, duration_minutes: int = 60):
        """Block an IP address temporarily."""
        self.blocked_ips.add(ip)
        
        # Schedule unblock (in production, use task queue)
        def unblock_later():
            time.sleep(duration_minutes * 60)
            self.blocked_ips.discard(ip)
        
        import threading
        threading.Thread(target=unblock_later, daemon=True).start()
    
    def validate_csrf_token(self, provided_token: str) -> bool:
        """Validate CSRF token against session token."""
        session_token = session.get('csrf_token')
        if not session_token or not provided_token:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return self._constant_time_compare(session_token, provided_token)
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """Constant time string comparison to prevent timing attacks."""
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0
    
    def validate_request_integrity(self, request_data: str = None) -> bool:
        """Validate request hasn't been tampered with."""
        # Basic integrity check (can be enhanced with HMAC)
        user_agent = request.headers.get('User-Agent', '')
        referer = request.headers.get('Referer', '')
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap',
            '<script', 'javascript:', 'data:', 'vbscript:'
        ]
        
        for pattern in suspicious_patterns:
            if pattern.lower() in user_agent.lower() or pattern.lower() in referer.lower():
                return False
        
        return True
    
    def log_security_event(self, event_type: str, details: Dict):
        """Log security events for monitoring."""
        timestamp = datetime.now().isoformat()
        ip = self.get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # In production, send to proper logging/SIEM system
        print(f"[SECURITY] {timestamp} - {event_type} from {ip}: {details} (UA: {user_agent})")
    
    def _setup_cleanup_task(self):
        """Setup periodic cleanup of rate limit storage."""
        def cleanup():
            while True:
                time.sleep(300)  # Clean every 5 minutes
                current_time = time.time()
                
                # Clean old rate limit entries
                for identifier in list(self.rate_limit_storage.keys()):
                    self.rate_limit_storage[identifier] = [
                        timestamp for timestamp in self.rate_limit_storage[identifier]
                        if current_time - timestamp < 3600  # Keep 1 hour of history
                    ]
                    
                    # Remove empty entries
                    if not self.rate_limit_storage[identifier]:
                        del self.rate_limit_storage[identifier]
        
        import threading
        threading.Thread(target=cleanup, daemon=True).start()

# Security decorators
def rate_limit(limit_type: str = 'api'):
    """Decorator to apply rate limiting to endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            security = getattr(current_app, 'security_middleware', None)
            if not security:
                return f(*args, **kwargs)
            
            ip = security.get_client_ip()
            if security.is_rate_limited(ip, limit_type):
                security.log_security_event('RATE_LIMIT_EXCEEDED', {
                    'limit_type': limit_type,
                    'endpoint': request.endpoint
                })
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def csrf_protected_enhanced(f):
    """Enhanced CSRF protection decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security = getattr(current_app, 'security_middleware', None)
        if not security:
            return f(*args, **kwargs)
        
        # Skip CSRF for GET requests
        if request.method == 'GET':
            return f(*args, **kwargs)
        
        # Get CSRF token from header or form data
        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        
        if not security.validate_csrf_token(csrf_token):
            security.log_security_event('CSRF_VALIDATION_FAILED', {
                'endpoint': request.endpoint,
                'method': request.method
            })
            return jsonify({'error': 'CSRF token validation failed'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def security_validated(f):
    """General security validation decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security = getattr(current_app, 'security_middleware', None)
        if not security:
            return f(*args, **kwargs)
        
        # Validate request integrity
        if not security.validate_request_integrity():
            security.log_security_event('SUSPICIOUS_REQUEST', {
                'endpoint': request.endpoint,
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            })
            return jsonify({'error': 'Request failed security validation'}), 400
        
        return f(*args, **kwargs)
    return decorated_function

def auth_rate_limited(category='auth'):
    """Rate limiting specifically for authentication endpoints.

    Can be used with or without parameters:
    - @auth_rate_limited (default 'auth' category)
    - @auth_rate_limited('custom_category')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            security = getattr(current_app, 'security_middleware', None)
            if not security:
                return f(*args, **kwargs)

            ip = security.get_client_ip()

            # Stricter rate limiting for auth endpoints
            if security.is_rate_limited(ip, category):
                # Block IP after repeated auth failures
                security.block_ip(ip, duration_minutes=30)
                security.log_security_event('AUTH_RATE_LIMIT_EXCEEDED', {
                    'endpoint': request.endpoint,
                    'category': category,
                    'action': 'IP_BLOCKED'
                })
                return jsonify({'error': 'Too many authentication attempts. IP temporarily blocked.'}), 429

            return f(*args, **kwargs)
        return decorated_function

    # Support both @auth_rate_limited and @auth_rate_limited('category')
    if callable(category):
        # Called without arguments: @auth_rate_limited
        func = category
        category = 'auth'
        return decorator(func)
    else:
        # Called with arguments: @auth_rate_limited('category')
        return decorator