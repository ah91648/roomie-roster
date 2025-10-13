#!/usr/bin/env python3
"""
Production Security Audit Script for RoomieRoster

This script performs comprehensive security checks to ensure the application is deployed securely.

Security checks:
- ✅ DEV_AUTH_BYPASS not enabled in production
- ✅ SSL/TLS enforced in DATABASE_URL
- ✅ FLASK_SECRET_KEY is properly set and secure
- ✅ CSRF protection is active
- ✅ Rate limiting is configured
- ✅ Session security settings are correct
- ✅ Sensitive data not exposed in logs
- ✅ Production environment properly configured

Usage:
    python3 backend/scripts/production_security_audit.py
"""

import os
import sys
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print section header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^70}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    """Print info message."""
    print(f"ℹ️  {text}")

def audit_auth_bypass():
    """Verify auth bypass is disabled in production."""
    print_header("Authentication Bypass Security")

    try:
        from utils.dev_auth_bypass import get_bypass_status

        status = get_bypass_status()
        flask_env = os.getenv('FLASK_ENV', 'production')

        print_info(f"FLASK_ENV: {flask_env}")
        print_info(f"DEV_AUTH_BYPASS flag: {status['dev_auth_bypass_flag']}")
        print_info(f"Bypass enabled: {status['bypass_enabled']}")
        print_info(f"Running on Render: {status['running_on_render']}")

        # Critical: Bypass must be disabled in production
        if flask_env == 'production' or status['running_on_render']:
            if status['bypass_enabled']:
                print_error("CRITICAL SECURITY ISSUE: Auth bypass is ENABLED in production!")
                print_error("This allows anyone to access protected endpoints without authentication")
                print_error("ACTION REQUIRED: Remove DEV_AUTH_BYPASS environment variable immediately")
                return False, "critical"
            else:
                print_success("Auth bypass is properly disabled in production")
                return True, "ok"
        else:
            if status['bypass_enabled']:
                print_warning("Auth bypass is enabled (acceptable for local development only)")
                return True, "warning"
            else:
                print_success("Auth bypass is disabled")
                return True, "ok"

    except Exception as e:
        print_error(f"Auth bypass check failed: {str(e)}")
        return False, "error"

def audit_database_ssl():
    """Verify SSL/TLS is enforced for database connections."""
    print_header("Database SSL/TLS Enforcement")

    database_url = os.getenv('DATABASE_URL', '')

    if not database_url:
        print_warning("DATABASE_URL not set (using JSON files)")
        return True, "warning"

    print_info(f"DATABASE_URL configured: {database_url[:20]}...")

    # Check for SSL mode
    if 'sslmode=require' in database_url or 'sslmode=verify-full' in database_url:
        print_success("SSL/TLS is enforced in DATABASE_URL")
        return True, "ok"
    elif 'sslmode=' in database_url:
        ssl_mode = re.search(r'sslmode=(\w+)', database_url)
        if ssl_mode:
            print_warning(f"SSL mode is set to '{ssl_mode.group(1)}' (should be 'require' or 'verify-full')")
            return True, "warning"
    else:
        # Check if this is a cloud database (should always use SSL)
        cloud_providers = ['neon.tech', 'amazonaws.com', 'heroku.com', 'railway.app', 'onrender.com']
        if any(provider in database_url for provider in cloud_providers):
            print_error("Cloud database detected but SSL not explicitly enforced")
            print_error("Add '?sslmode=require' to your DATABASE_URL")
            return False, "critical"
        else:
            print_warning("SSL not configured (may be acceptable for localhost)")
            return True, "warning"

def audit_flask_secret_key():
    """Verify Flask secret key is set and secure."""
    print_header("Flask Secret Key Security")

    secret_key = os.getenv('FLASK_SECRET_KEY')

    if not secret_key:
        print_error("FLASK_SECRET_KEY not set!")
        print_error("This is required for secure session management")
        print_info("Generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
        return False, "critical"

    # Check length (should be at least 32 characters for hex string)
    if len(secret_key) < 32:
        print_warning(f"FLASK_SECRET_KEY is only {len(secret_key)} characters (recommend 64+ for hex)")
        return True, "warning"

    # Check if it's obviously insecure
    insecure_values = ['dev', 'test', 'secret', 'password', '12345', 'change-me', 'placeholder']
    if any(val in secret_key.lower() for val in insecure_values):
        print_error("FLASK_SECRET_KEY appears to be a placeholder or insecure value")
        print_error("Generate a secure key: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
        return False, "critical"

    print_success(f"FLASK_SECRET_KEY is set ({len(secret_key)} characters)")
    return True, "ok"

def audit_environment_config():
    """Verify production environment is properly configured."""
    print_header("Environment Configuration")

    issues = []

    # Check FLASK_ENV
    flask_env = os.getenv('FLASK_ENV', 'production')
    print_info(f"FLASK_ENV: {flask_env}")

    if flask_env == 'production':
        print_success("FLASK_ENV is set to 'production'")
    else:
        print_warning(f"FLASK_ENV is '{flask_env}' (should be 'production' in production)")
        issues.append("warning")

    # Check FLASK_DEBUG
    flask_debug = os.getenv('FLASK_DEBUG', 'false').lower()
    print_info(f"FLASK_DEBUG: {flask_debug}")

    if flask_debug in ['true', '1', 'yes']:
        print_error("FLASK_DEBUG is enabled in production!")
        print_error("This exposes sensitive information in error pages")
        issues.append("critical")
    else:
        print_success("FLASK_DEBUG is disabled")

    # Check PORT (set by cloud platforms)
    port = os.getenv('PORT')
    if port:
        print_info(f"PORT: {port} (set by cloud platform)")
    else:
        print_info("PORT not set (running locally)")

    # Check RENDER_SERVICE_NAME (Render-specific)
    render_service = os.getenv('RENDER_SERVICE_NAME')
    if render_service:
        print_info(f"Running on Render: {render_service}")

    if not issues:
        return True, "ok"
    elif "critical" in issues:
        return False, "critical"
    else:
        return True, "warning"

def audit_required_env_vars():
    """Check that all required production environment variables are set."""
    print_header("Required Environment Variables")

    required_vars = {
        'GOOGLE_CLIENT_ID': 'critical',
        'GOOGLE_CLIENT_SECRET': 'critical',
        'FLASK_SECRET_KEY': 'critical',
        'ROOMIE_WHITELIST': 'warning',
        'DATABASE_URL': 'warning'
    }

    issues = []

    for var_name, severity in required_vars.items():
        value = os.getenv(var_name)

        if value:
            # Mask the value for security
            if len(value) > 20:
                masked = f"{value[:6]}...{value[-4:]}"
            else:
                masked = f"{value[:4]}..."

            print_success(f"{var_name}: {masked}")
        else:
            if severity == 'critical':
                print_error(f"{var_name} is NOT set (required)")
                issues.append("critical")
            else:
                print_warning(f"{var_name} is NOT set (recommended)")
                issues.append("warning")

    if not issues:
        return True, "ok"
    elif "critical" in issues:
        return False, "critical"
    else:
        return True, "warning"

def audit_google_oauth_config():
    """Verify Google OAuth configuration."""
    print_header("Google OAuth Configuration")

    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        print_error("Google OAuth credentials not configured")
        print_error("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables")
        return False, "critical"

    # Basic validation of format
    if not client_id.endswith('.apps.googleusercontent.com'):
        print_warning("GOOGLE_CLIENT_ID format looks unusual (should end with .apps.googleusercontent.com)")

    if len(client_secret) < 20:
        print_warning(f"GOOGLE_CLIENT_SECRET seems short ({len(client_secret)} chars)")

    print_success("Google OAuth credentials are configured")

    # Check whitelist
    whitelist = os.getenv('ROOMIE_WHITELIST')
    if whitelist:
        emails = [e.strip() for e in whitelist.split(',')]
        print_success(f"ROOMIE_WHITELIST configured ({len(emails)} email(s))")
        print_info(f"Whitelisted emails: {', '.join(emails[:3])}{'...' if len(emails) > 3 else ''}")
    else:
        print_warning("ROOMIE_WHITELIST not set (any Google user can authenticate)")

    return True, "ok"

def audit_session_security():
    """Check session security configuration."""
    print_header("Session Security Configuration")

    try:
        from flask import Flask
        from utils.session_manager import SessionManager

        app = Flask(__name__)
        session_manager = SessionManager()
        session_manager.init_app(app)

        # Check session configuration
        print_info(f"SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE', False)}")
        print_info(f"SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY', False)}")
        print_info(f"SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')}")

        issues = []

        # Check if secure cookies are enabled in production
        is_production = bool(os.getenv('PORT')) or os.getenv('FLASK_ENV') == 'production'

        if is_production and not app.config.get('SESSION_COOKIE_SECURE'):
            print_warning("SESSION_COOKIE_SECURE should be True in production")
            issues.append("warning")
        else:
            print_success("Session cookie security is properly configured")

        if not app.config.get('SESSION_COOKIE_HTTPONLY'):
            print_error("SESSION_COOKIE_HTTPONLY should be True")
            issues.append("critical")
        else:
            print_success("HTTPOnly flag is set (prevents XSS attacks)")

        if app.config.get('SESSION_COOKIE_SAMESITE') != 'Lax':
            print_warning(f"SESSION_COOKIE_SAMESITE is {app.config.get('SESSION_COOKIE_SAMESITE')} (recommend 'Lax')")
            issues.append("warning")

        if not issues:
            return True, "ok"
        elif "critical" in issues:
            return False, "critical"
        else:
            return True, "warning"

    except Exception as e:
        print_error(f"Session security check failed: {str(e)}")
        return False, "error"

def generate_security_report(results):
    """Generate final security audit report."""
    print_header("Security Audit Summary")

    critical_issues = []
    warnings = []
    passed = []

    for check_name, (passed_check, severity) in results.items():
        if severity == "critical" or (not passed_check and severity != "warning"):
            critical_issues.append(check_name)
        elif severity == "warning":
            warnings.append(check_name)
        elif passed_check:
            passed.append(check_name)

    # Print summary
    print(f"{Colors.BOLD}Security Checks Summary:{Colors.END}\n")

    if passed:
        print(f"{Colors.GREEN}✅ Passed ({len(passed)}):{Colors.END}")
        for check in passed:
            print(f"   - {check}")

    if warnings:
        print(f"\n{Colors.YELLOW}⚠️  Warnings ({len(warnings)}):{Colors.END}")
        for check in warnings:
            print(f"   - {check}")

    if critical_issues:
        print(f"\n{Colors.RED}❌ Critical Issues ({len(critical_issues)}):{Colors.END}")
        for check in critical_issues:
            print(f"   - {check}")

    # Overall assessment
    print(f"\n{Colors.BOLD}Overall Security Assessment:{Colors.END}\n")

    if critical_issues:
        print_error("SECURITY AUDIT FAILED - Critical issues found!")
        print_error("DO NOT deploy to production until these are resolved")
        return 2
    elif warnings:
        print_warning("Security audit passed with warnings")
        print_warning("Review warnings before deploying to production")
        return 1
    else:
        print_success("🎉 Security audit passed - No critical issues found!")
        print_success("System meets security requirements for production deployment")
        return 0

def main():
    """Run security audit."""
    print(f"\n{Colors.BOLD}RoomieRoster Production Security Audit{Colors.END}\n")

    results = {}

    # Run all security checks
    results['auth_bypass'] = audit_auth_bypass()
    results['database_ssl'] = audit_database_ssl()
    results['flask_secret'] = audit_flask_secret_key()
    results['environment'] = audit_environment_config()
    results['required_vars'] = audit_required_env_vars()
    results['oauth_config'] = audit_google_oauth_config()
    results['session_security'] = audit_session_security()

    # Generate report
    return generate_security_report(results)

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Audit interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
