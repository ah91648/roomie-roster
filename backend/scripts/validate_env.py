#!/usr/bin/env python3
"""
Environment variable validation script for RoomieRoster.

This script validates that all required environment variables are properly configured
and checks for common security issues.

Usage:
    python scripts/validate_env.py
"""

import os
import re
import sys


class ValidationResult:
    """Stores validation results"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []

    def add_error(self, message):
        self.errors.append(f"❌ ERROR: {message}")

    def add_warning(self, message):
        self.warnings.append(f"⚠️  WARNING: {message}")

    def add_success(self, message):
        self.successes.append(f"✅ {message}")

    def print_results(self):
        """Print all validation results"""
        print("\n" + "=" * 60)
        print("Environment Validation Results")
        print("=" * 60)

        if self.successes:
            print("\n✅ Passed Checks:")
            for success in self.successes:
                print(f"  {success}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  {warning}")

        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  {error}")

        print("\n" + "=" * 60)

        if self.errors:
            print("❌ VALIDATION FAILED - Fix errors before deploying")
            print("=" * 60)
            return False
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
            print("=" * 60)
            return True
        else:
            print("✅ VALIDATION PASSED - All checks successful")
            print("=" * 60)
            return True


def validate_database_url(result):
    """Validate DATABASE_URL configuration"""
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        result.add_error("DATABASE_URL is not set")
        return

    # Check PostgreSQL prefix
    if not db_url.startswith('postgresql://'):
        result.add_error("DATABASE_URL must start with 'postgresql://'")

    # Check for SSL mode
    if '?sslmode=require' not in db_url and '&sslmode=require' not in db_url:
        result.add_warning("DATABASE_URL should include '?sslmode=require' for security")

    # Check for obvious placeholder values
    placeholders = ['localhost', 'user:pass', 'YOUR_PASSWORD', 'XXXXX']
    if any(placeholder in db_url for placeholder in placeholders):
        result.add_error("DATABASE_URL appears to contain placeholder values")
    else:
        result.add_success("DATABASE_URL configured correctly")


def validate_google_oauth(result):
    """Validate Google OAuth credentials"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    # Validate Client ID
    if not client_id:
        result.add_error("GOOGLE_CLIENT_ID is not set")
    elif not client_id.endswith('.apps.googleusercontent.com'):
        result.add_error("GOOGLE_CLIENT_ID has invalid format (should end with .apps.googleusercontent.com)")
    elif 'XXXXX' in client_id or 'your-client-id' in client_id.lower():
        result.add_error("GOOGLE_CLIENT_ID appears to be a placeholder")
    else:
        result.add_success("GOOGLE_CLIENT_ID configured")

    # Validate Client Secret
    if not client_secret:
        result.add_error("GOOGLE_CLIENT_SECRET is not set")
    elif not client_secret.startswith('GOCSPX-'):
        result.add_warning("GOOGLE_CLIENT_SECRET has unexpected format (should start with GOCSPX-)")
    elif len(client_secret) < 20:
        result.add_error("GOOGLE_CLIENT_SECRET is too short (likely invalid)")
    elif 'YourClientSecret' in client_secret or 'XXXXX' in client_secret:
        result.add_error("GOOGLE_CLIENT_SECRET appears to be a placeholder")
    else:
        result.add_success("GOOGLE_CLIENT_SECRET configured")


def validate_flask_secret(result):
    """Validate Flask secret key"""
    secret_key = os.getenv('FLASK_SECRET_KEY')

    if not secret_key:
        result.add_error("FLASK_SECRET_KEY is not set")
        return

    # Check length
    if len(secret_key) < 32:
        result.add_error(f"FLASK_SECRET_KEY is too short ({len(secret_key)} chars, minimum 32)")

    # Check for common weak values
    weak_values = [
        'dev', 'secret', 'key', 'password', 'change_me',
        'your_secret_key_here', 'replace_with_actual_secret',
        'your_64_character_hex_string_here'
    ]

    if secret_key.lower() in weak_values:
        result.add_error("FLASK_SECRET_KEY is using a common/placeholder value")
    elif secret_key == secret_key.lower() and not re.match(r'^[a-f0-9]+$', secret_key):
        result.add_warning("FLASK_SECRET_KEY should be a random hex string")
    else:
        if len(secret_key) >= 64:
            result.add_success(f"FLASK_SECRET_KEY is strong ({len(secret_key)} characters)")
        else:
            result.add_success(f"FLASK_SECRET_KEY configured ({len(secret_key)} characters)")


def validate_whitelist(result):
    """Validate roommate whitelist"""
    whitelist = os.getenv('ROOMIE_WHITELIST')

    if not whitelist:
        result.add_error("ROOMIE_WHITELIST is not set")
        return

    # Check for placeholder values
    if 'example.com' in whitelist or 'user1@' in whitelist or 'gmail.com' in whitelist:
        result.add_warning("ROOMIE_WHITELIST may contain placeholder email addresses")

    # Parse emails
    emails = [e.strip() for e in whitelist.split(',')]

    # Validate email format
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    invalid_emails = [e for e in emails if not re.match(email_regex, e)]

    if invalid_emails:
        result.add_error(f"ROOMIE_WHITELIST contains invalid emails: {', '.join(invalid_emails)}")
    elif len(emails) < 1:
        result.add_error("ROOMIE_WHITELIST must contain at least one email")
    else:
        result.add_success(f"ROOMIE_WHITELIST configured with {len(emails)} email(s)")


def validate_flask_environment(result):
    """Validate Flask environment settings"""
    flask_env = os.getenv('FLASK_ENV')

    if not flask_env:
        result.add_warning("FLASK_ENV is not set (defaults to 'production')")
    elif flask_env == 'production':
        result.add_success("FLASK_ENV set to 'production'")
    else:
        result.add_warning(f"FLASK_ENV='{flask_env}' (should be 'production' for deployment)")


def check_security_issues(result):
    """Check for security configuration issues"""

    # Check FLASK_DEBUG
    flask_debug = os.getenv('FLASK_DEBUG')
    if flask_debug and flask_debug.lower() in ('true', '1', 'yes'):
        result.add_error("FLASK_DEBUG is enabled - MUST be disabled in production")
    else:
        result.add_success("FLASK_DEBUG is disabled")

    # Check DEV_AUTH_BYPASS
    dev_auth = os.getenv('DEV_AUTH_BYPASS')
    if dev_auth and dev_auth.lower() in ('true', '1', 'yes'):
        result.add_error("DEV_AUTH_BYPASS is enabled - MUST be disabled in production")
    else:
        result.add_success("DEV_AUTH_BYPASS is disabled")

    # Check TESTING
    testing = os.getenv('TESTING')
    if testing and testing.lower() in ('true', '1', 'yes'):
        result.add_warning("TESTING mode is enabled - should be disabled in production")


def validate_optional_vars(result):
    """Validate optional configuration"""

    # APP_BASE_URL
    base_url = os.getenv('APP_BASE_URL')
    if base_url:
        if not base_url.startswith('https://'):
            result.add_warning("APP_BASE_URL should use HTTPS in production")
        else:
            result.add_success(f"APP_BASE_URL configured: {base_url}")

    # OAUTHLIB_RELAX_TOKEN_SCOPE
    oauth_relax = os.getenv('OAUTHLIB_RELAX_TOKEN_SCOPE')
    if oauth_relax:
        result.add_success("OAUTHLIB_RELAX_TOKEN_SCOPE configured")


def main():
    """Run all validation checks"""
    print("\n" + "=" * 60)
    print("RoomieRoster Environment Variable Validation")
    print("=" * 60)

    result = ValidationResult()

    # Run all validations
    print("\nValidating environment configuration...")

    validate_database_url(result)
    validate_google_oauth(result)
    validate_flask_secret(result)
    validate_whitelist(result)
    validate_flask_environment(result)
    check_security_issues(result)
    validate_optional_vars(result)

    # Print results
    success = result.print_results()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
