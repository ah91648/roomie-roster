#!/usr/bin/env python3
"""
Script to add @login_required decorator to all unprotected API endpoints.
This ensures that only authenticated users can access the RoomieRoster application.
"""

import re
import os

# Endpoints that should NOT have @login_required (they need to be public)
EXEMPT_ENDPOINTS = [
    '/api/health',              # Health check endpoint
    '/api/auth/google-login',   # Initiate OAuth login
    '/api/auth/callback',       # OAuth callback
    '/api/auth/status',         # Check if auth is configured
    '/api/debug/oauth-config',  # Debug endpoint (optional, can be protected later)
]

def should_add_login_required(route_path, current_decorators):
    """
    Determine if @login_required should be added to this endpoint.
    
    Args:
        route_path: The API route path (e.g., '/api/chores')
        current_decorators: List of decorators already applied
    
    Returns:
        bool: True if @login_required should be added
    """
    # Check if endpoint is in exemption list
    if route_path in EXEMPT_ENDPOINTS:
        return False
    
    # Check if @login_required is already present
    if '@login_required' in current_decorators:
        return False
    
    # Check if it's a catch-all route (serve static files)
    if "'<path:path>'" in route_path or '"<path:path>"' in route_path:
        return False
    
    return True

def add_login_required_decorators(file_path):
    """
    Add @login_required decorator to all unprotected API endpoints in app.py.
    
    Args:
        file_path: Path to app.py file
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified_lines = []
    i = 0
    endpoints_modified = []
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line is an @app.route decorator
        if line.strip().startswith('@app.route('):
            # Extract the route path
            route_match = re.search(r"@app\.route\('([^']+)'", line)
            if not route_match:
                route_match = re.search(r'@app\.route\("([^"]+)"', line)
            
            if route_match:
                route_path = route_match.group(1)
                
                # Look ahead to see what decorators are already present
                decorators = []
                j = i + 1
                while j < len(lines) and (lines[j].strip().startswith('@') or lines[j].strip() == ''):
                    if lines[j].strip().startswith('@'):
                        decorators.append(lines[j].strip())
                    j += 1
                
                # Determine if we should add @login_required
                if should_add_login_required(route_path, decorators):
                    # Add the current line (@app.route)
                    modified_lines.append(line)
                    
                    # Add @login_required on the next line with proper indentation
                    indent = len(line) - len(line.lstrip())
                    modified_lines.append(' ' * indent + '@login_required\n')
                    
                    endpoints_modified.append(route_path)
                    i += 1
                    continue
        
        # Add the line as-is
        modified_lines.append(line)
        i += 1
    
    # Write the modified content back to the file
    with open(file_path, 'w') as f:
        f.writelines(modified_lines)
    
    return endpoints_modified

def main():
    """Main function to run the script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_py_path = os.path.join(script_dir, 'app.py')
    
    if not os.path.exists(app_py_path):
        print(f"ERROR: app.py not found at {app_py_path}")
        return 1
    
    print("Adding @login_required decorators to unprotected endpoints...")
    print(f"Modifying file: {app_py_path}")
    print()
    
    # Create a backup first
    backup_path = app_py_path + '.backup'
    with open(app_py_path, 'r') as src:
        with open(backup_path, 'w') as dst:
            dst.write(src.read())
    print(f"Created backup: {backup_path}")
    print()
    
    # Add the decorators
    modified_endpoints = add_login_required_decorators(app_py_path)
    
    # Report results
    print(f"✅ Successfully modified {len(modified_endpoints)} endpoints:")
    print()
    for endpoint in sorted(modified_endpoints):
        print(f"  - {endpoint}")
    
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Total endpoints protected: {len(modified_endpoints)}")
    print(f"  Backup saved to: {backup_path}")
    print()
    print("⚠️  IMPORTANT: Please review the changes before deploying!")
    print("   Run: diff app.py.backup app.py")
    print()
    
    return 0

if __name__ == '__main__':
    exit(main())
