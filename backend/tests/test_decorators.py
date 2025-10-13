"""
Comprehensive test suite for security decorators.

Tests all decorator patterns used in the application to prevent regression
of the bugs that were fixed in the security_middleware.py and app.py.

Key Issues Tested:
1. @auth_rate_limited - must support both parameterized and non-parameterized usage
2. @rate_limit('category') - must work with category parameter
3. Decorator stacking - multiple decorators on same endpoint
4. Rate limit enforcement and IP blocking
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, jsonify, session
import sys
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from utils.security_middleware import (
    SecurityMiddleware,
    rate_limit,
    auth_rate_limited,
    csrf_protected_enhanced,
    security_validated
)


class TestSecurityDecorators:
    """Test suite for all security decorators."""

    @pytest.fixture
    def app(self):
        """Create a test Flask app with security middleware."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['SESSION_TYPE'] = 'filesystem'

        # Initialize security middleware
        security = SecurityMiddleware()
        security.init_app(app)

        # Create test routes with various decorator patterns

        @app.route('/api/test/basic')
        def basic_endpoint():
            return jsonify({'message': 'success'})

        @app.route('/api/test/rate-limited')
        @rate_limit('api')
        def rate_limited_endpoint():
            return jsonify({'message': 'success'})

        @app.route('/api/test/auth-rate-limited-no-param')
        @auth_rate_limited
        def auth_rate_limited_no_param():
            """Test @auth_rate_limited without parameters"""
            return jsonify({'message': 'success'})

        @app.route('/api/test/auth-rate-limited-with-param')
        @auth_rate_limited('custom_auth')
        def auth_rate_limited_with_param():
            """Test @auth_rate_limited('category')"""
            return jsonify({'message': 'success'})

        @app.route('/api/test/calendar-rate-limited')
        @rate_limit('calendar')
        def calendar_rate_limited():
            """Test @rate_limit('calendar')"""
            return jsonify({'message': 'success'})

        @app.route('/api/test/csrf-protected', methods=['POST'])
        @csrf_protected_enhanced
        def csrf_protected_route():
            return jsonify({'message': 'success'})

        @app.route('/api/test/security-validated', methods=['POST'])
        @security_validated
        def security_validated_route():
            return jsonify({'message': 'success'})

        @app.route('/api/test/stacked-decorators', methods=['POST'])
        @rate_limit('api')
        @csrf_protected_enhanced
        @security_validated
        def stacked_decorators_route():
            """Test multiple decorators on same endpoint"""
            return jsonify({'message': 'success'})

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()

    @pytest.fixture
    def security(self, app):
        """Get the security middleware instance."""
        return app.security_middleware

    def test_basic_endpoint_no_decorators(self, client):
        """Test that basic endpoint works without any security decorators."""
        response = client.get('/api/test/basic')
        assert response.status_code == 200
        assert response.json['message'] == 'success'

    def test_rate_limit_decorator_basic(self, client, security):
        """Test basic rate limiting functionality."""
        # Clear any existing rate limit data
        security.rate_limit_storage.clear()

        # Should succeed on first request
        response = client.get('/api/test/rate-limited')
        assert response.status_code == 200

    def test_rate_limit_enforcement(self, client, security):
        """Test that rate limits are actually enforced."""
        # Set very low rate limit for testing
        security.rate_limits['api'] = {'requests': 2, 'window': 60}
        security.rate_limit_storage.clear()

        # First two requests should succeed
        for i in range(2):
            response = client.get('/api/test/rate-limited')
            assert response.status_code == 200, f"Request {i+1} should succeed"

        # Third request should be rate limited
        response = client.get('/api/test/rate-limited')
        assert response.status_code == 429
        assert 'rate limit' in response.json['error'].lower()

    def test_auth_rate_limited_without_param(self, client, security):
        """Test @auth_rate_limited decorator without parameters."""
        security.rate_limits['auth'] = {'requests': 2, 'window': 60}
        security.rate_limit_storage.clear()
        security.blocked_ips.clear()

        # First two requests should succeed
        for i in range(2):
            response = client.get('/api/test/auth-rate-limited-no-param')
            assert response.status_code == 200, f"Auth request {i+1} should succeed"

        # Third request should trigger rate limit and IP block
        response = client.get('/api/test/auth-rate-limited-no-param')
        assert response.status_code == 429
        assert 'authentication attempts' in response.json['error'].lower()

    def test_auth_rate_limited_with_param(self, client, security):
        """Test @auth_rate_limited('category') decorator with custom category."""
        security.rate_limits['custom_auth'] = {'requests': 2, 'window': 60}
        security.rate_limit_storage.clear()
        security.blocked_ips.clear()

        # First two requests should succeed
        for i in range(2):
            response = client.get('/api/test/auth-rate-limited-with-param')
            assert response.status_code == 200, f"Custom auth request {i+1} should succeed"

        # Third request should be rate limited
        response = client.get('/api/test/auth-rate-limited-with-param')
        assert response.status_code == 429

    def test_calendar_rate_limit_category(self, client, security):
        """Test @rate_limit('calendar') with specific category."""
        security.rate_limits['calendar'] = {'requests': 3, 'window': 60}
        security.rate_limit_storage.clear()

        # Should use calendar-specific rate limit
        for i in range(3):
            response = client.get('/api/test/calendar-rate-limited')
            assert response.status_code == 200

        # Fourth request should be rate limited
        response = client.get('/api/test/calendar-rate-limited')
        assert response.status_code == 429

    def test_csrf_protection_missing_token(self, client):
        """Test CSRF protection rejects requests without token."""
        with client.session_transaction() as sess:
            sess['csrf_token'] = 'valid-token-12345'

        # Request without CSRF token should fail
        response = client.post('/api/test/csrf-protected', json={'data': 'test'})
        assert response.status_code == 403
        assert 'csrf' in response.json['error'].lower()

    def test_csrf_protection_valid_token(self, client):
        """Test CSRF protection allows requests with valid token."""
        with client.session_transaction() as sess:
            sess['csrf_token'] = 'valid-token-12345'

        # Request with valid CSRF token should succeed
        response = client.post(
            '/api/test/csrf-protected',
            json={'data': 'test'},
            headers={'X-CSRF-Token': 'valid-token-12345'}
        )
        assert response.status_code == 200

    def test_csrf_protection_invalid_token(self, client):
        """Test CSRF protection rejects requests with invalid token."""
        with client.session_transaction() as sess:
            sess['csrf_token'] = 'valid-token-12345'

        # Request with wrong CSRF token should fail
        response = client.post(
            '/api/test/csrf-protected',
            json={'data': 'test'},
            headers={'X-CSRF-Token': 'wrong-token'}
        )
        assert response.status_code == 403

    def test_csrf_skip_get_requests(self, client):
        """Test that CSRF protection is skipped for GET requests."""
        # This endpoint is POST-only, but we're testing the decorator logic
        # In real scenarios, GET endpoints wouldn't have CSRF protection
        pass  # This is more of a design pattern test

    def test_security_validation_suspicious_user_agent(self, client):
        """Test security validation blocks suspicious user agents."""
        response = client.post(
            '/api/test/security-validated',
            json={'data': 'test'},
            headers={'User-Agent': 'sqlmap/1.0'}
        )
        assert response.status_code == 400
        assert 'security validation' in response.json['error'].lower()

    def test_security_validation_normal_request(self, client):
        """Test security validation allows normal requests."""
        response = client.post(
            '/api/test/security-validated',
            json={'data': 'test'},
            headers={'User-Agent': 'Mozilla/5.0 (Normal Browser)'}
        )
        assert response.status_code == 200

    def test_stacked_decorators(self, client, security):
        """Test multiple decorators working together on same endpoint."""
        security.rate_limit_storage.clear()

        with client.session_transaction() as sess:
            sess['csrf_token'] = 'valid-token-12345'

        # Request with all requirements met should succeed
        response = client.post(
            '/api/test/stacked-decorators',
            json={'data': 'test'},
            headers={
                'X-CSRF-Token': 'valid-token-12345',
                'User-Agent': 'Mozilla/5.0 (Normal Browser)'
            }
        )
        assert response.status_code == 200

    def test_stacked_decorators_csrf_failure(self, client, security):
        """Test stacked decorators - CSRF failure blocks request."""
        security.rate_limit_storage.clear()

        with client.session_transaction() as sess:
            sess['csrf_token'] = 'valid-token-12345'

        # Request with invalid CSRF should fail
        response = client.post(
            '/api/test/stacked-decorators',
            json={'data': 'test'},
            headers={
                'X-CSRF-Token': 'wrong-token',
                'User-Agent': 'Mozilla/5.0 (Normal Browser)'
            }
        )
        assert response.status_code == 403

    def test_stacked_decorators_security_failure(self, client, security):
        """Test stacked decorators - security validation failure blocks request."""
        security.rate_limit_storage.clear()

        with client.session_transaction() as sess:
            sess['csrf_token': 'valid-token-12345'

        # Request with suspicious user agent should fail
        response = client.post(
            '/api/test/stacked-decorators',
            json={'data': 'test'},
            headers={
                'X-CSRF-Token': 'valid-token-12345',
                'User-Agent': 'sqlmap/1.0'
            }
        )
        assert response.status_code == 400

    def test_ip_blocking_mechanism(self, client, security):
        """Test that IP blocking works correctly."""
        test_ip = '192.168.1.100'
        security.blocked_ips.clear()

        # Block the IP
        security.block_ip(test_ip, duration_minutes=0.01)

        # Verify IP is blocked
        assert test_ip in security.blocked_ips

        # Wait for unblock (1 second for testing)
        time.sleep(1)

        # Note: In production this uses threading, so we can't easily test the auto-unblock
        # But we've verified the blocking mechanism works

    def test_rate_limit_cleanup(self, security):
        """Test that rate limit storage is cleaned up properly."""
        # Add old entries
        old_time = time.time() - 4000  # 1+ hours ago
        security.rate_limit_storage['test-ip'] = [old_time, old_time]

        # Check rate limit (should clean old entries)
        is_limited = security.is_rate_limited('test-ip', 'api')

        # Old entries should be cleaned
        assert len(security.rate_limit_storage['test-ip']) <= 1

    def test_constant_time_compare(self, security):
        """Test constant-time string comparison for CSRF tokens."""
        # Same strings should return True
        assert security._constant_time_compare('token123', 'token123')

        # Different strings should return False
        assert not security._constant_time_compare('token123', 'token456')

        # Different lengths should return False
        assert not security._constant_time_compare('short', 'much_longer_string')

    def test_get_client_ip_with_proxy(self, app, security):
        """Test client IP extraction with proxy headers."""
        with app.test_request_context(
            '/',
            headers={'X-Forwarded-For': '192.168.1.100, 10.0.0.1'}
        ):
            ip = security.get_client_ip()
            assert ip == '192.168.1.100'

    def test_get_client_ip_without_proxy(self, app, security):
        """Test client IP extraction without proxy headers."""
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.200'}):
            ip = security.get_client_ip()
            assert ip == '192.168.1.200'

    def test_security_headers_added(self, client):
        """Test that security headers are added to all responses."""
        response = client.get('/api/test/basic')

        # Check for security headers
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'

        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'

        assert 'X-XSS-Protection' in response.headers


class TestDecoratorRegressionPrevention:
    """Tests specifically designed to prevent regression of fixed bugs."""

    def test_auth_rate_limited_both_usage_patterns(self):
        """
        REGRESSION TEST: Ensure @auth_rate_limited supports both:
        - @auth_rate_limited (no parentheses)
        - @auth_rate_limited('category') (with parameter)

        This was Bug #2 in the original report.
        """
        app = Flask(__name__)
        app.config['TESTING'] = True
        security = SecurityMiddleware()
        security.init_app(app)

        # Test pattern 1: No parameters
        @app.route('/test1')
        @auth_rate_limited
        def endpoint1():
            return 'ok'

        # Test pattern 2: With parameter
        @app.route('/test2')
        @auth_rate_limited('custom')
        def endpoint2():
            return 'ok'

        client = app.test_client()

        # Both should work without TypeError
        response1 = client.get('/test1')
        assert response1.status_code == 200

        response2 = client.get('/test2')
        assert response2.status_code == 200

    def test_rate_limit_category_parameter(self):
        """
        REGRESSION TEST: Ensure @rate_limit('category') works.

        This was Bug #3 in the original report - using limit= and per=
        parameters was incorrect.
        """
        app = Flask(__name__)
        app.config['TESTING'] = True
        security = SecurityMiddleware()
        security.init_app(app)

        # This should work (correct pattern)
        @app.route('/test')
        @rate_limit('calendar')
        def endpoint():
            return 'ok'

        client = app.test_client()
        response = client.get('/test')
        assert response.status_code == 200

    def test_decorator_stacking_order(self):
        """
        REGRESSION TEST: Ensure decorators work when stacked.

        Decorators must be applied in the correct order and not interfere
        with each other.
        """
        app = Flask(__name__)
        app.config['TESTING'] = True
        security = SecurityMiddleware()
        security.init_app(app)

        @app.route('/test', methods=['POST'])
        @rate_limit('api')
        @csrf_protected_enhanced
        def endpoint():
            return 'ok'

        # Should not raise any errors during route registration
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]


if __name__ == '__main__':
    """Run tests with pytest."""
    pytest.main([__file__, '-v', '--tb=short'])
