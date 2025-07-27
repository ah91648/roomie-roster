#!/usr/bin/env python3
"""
RoomieRoster Application Launcher

This script automatically launches both the Flask backend and React frontend
for the RoomieRoster household chore management application.

Usage:
    python3 launch_app.py

Requirements:
    - Python 3.8+ with pip
    - Node.js 16+ with npm
    - Backend dependencies installed (pip install -r backend/requirements.txt)
    - Frontend dependencies installed (npm install in frontend directory)
"""

import os
import sys
import time
import signal
import subprocess
import threading
import webbrowser
import socket
import queue
import urllib.request
from pathlib import Path

class RoomieRosterLauncher:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.backend_dir = self.script_dir / "backend"
        self.frontend_dir = self.script_dir / "frontend"
        self.backend_process = None
        self.frontend_process = None
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def print_banner(self):
        """Print the application banner"""
        print("=" * 60)
        print("🏠 RoomieRoster Application Launcher")
        print("   Household Chore Management Made Easy")
        print("=" * 60)
        print()
    
    def check_requirements(self):
        """Check if all requirements are met"""
        print("🔍 Checking requirements...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ is required")
            return False
        print(f"✅ Python {sys.version.split()[0]} detected")
        
        # Check if directories exist
        if not self.backend_dir.exists():
            print("❌ Backend directory not found")
            return False
        print("✅ Backend directory found")
        
        if not self.frontend_dir.exists():
            print("❌ Frontend directory not found")
            return False
        print("✅ Frontend directory found")
        
        # Check for requirements.txt
        requirements_file = self.backend_dir / "requirements.txt"
        if not requirements_file.exists():
            print("❌ Backend requirements.txt not found")
            return False
        print("✅ Backend requirements.txt found")
        
        # Check for package.json
        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            print("❌ Frontend package.json not found")
            return False
        print("✅ Frontend package.json found")
        
        # Check for Node.js
        try:
            result = subprocess.run(["node", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                print(f"✅ Node.js {node_version} detected")
            else:
                print("❌ Node.js not found or not working")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Node.js not found in PATH")
            return False
        
        # Check for npm
        try:
            result = subprocess.run(["npm", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                print(f"✅ npm {npm_version} detected")
            else:
                print("❌ npm not found or not working")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ npm not found in PATH")
            return False
        
        print("✅ All requirements met!")
        print()
        return True
    
    def install_dependencies(self):
        """Install missing dependencies if needed"""
        print("📦 Checking and installing dependencies...")
        
        # Check backend dependencies
        print("   Checking backend dependencies...")
        try:
            # Try importing required modules
            import flask
            import flask_cors
            print("   ✅ Backend dependencies already installed")
        except ImportError:
            print("   📥 Installing backend dependencies...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", 
                    str(self.backend_dir / "requirements.txt")
                ], check=True, cwd=self.backend_dir)
                print("   ✅ Backend dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Failed to install backend dependencies: {e}")
                return False
        
        # Check frontend dependencies
        print("   Checking frontend dependencies...")
        node_modules = self.frontend_dir / "node_modules"
        if not node_modules.exists():
            print("   📥 Installing frontend dependencies...")
            try:
                subprocess.run(["npm", "install"], 
                             check=True, cwd=self.frontend_dir)
                print("   ✅ Frontend dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Failed to install frontend dependencies: {e}")
                return False
        else:
            print("   ✅ Frontend dependencies already installed")
        
        print("✅ All dependencies ready!")
        print()
        return True
    
    def check_port_available(self, port):
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result != 0  # 0 means connection successful (port in use)
        except Exception:
            return True  # Assume available if we can't check
    
    def test_flask_imports(self):
        """Test Flask imports before starting subprocess"""
        try:
            # Test if we can import and create a basic Flask app
            import sys
            import subprocess
            
            test_code = """
import sys
sys.path.insert(0, '.')
try:
    from utils.data_handler import DataHandler
    from utils.assignment_logic import ChoreAssignmentLogic
    from flask import Flask
    from flask_cors import CORS
    print('IMPORT_SUCCESS')
except Exception as e:
    print(f'IMPORT_ERROR: {e}')
    sys.exit(1)
"""
            
            result = subprocess.run(
                [sys.executable, '-c', test_code],
                cwd=self.backend_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if 'IMPORT_SUCCESS' in result.stdout:
                return True, None
            else:
                error_msg = result.stderr or result.stdout
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
    
    def start_backend(self):
        """Start the Flask backend server with enhanced error capture"""
        print("🚀 Starting Flask backend server...")
        
        # Try ports 5000, 5001, 5002 until we find an available one
        backend_port = None
        for port in [5000, 5001, 5002]:
            if self.check_port_available(port):
                backend_port = port
                break
        
        if backend_port is None:
            print("❌ Ports 5000-5002 are all in use. Please stop one of the services and try again.")
            print("   You can check what's using the ports with: lsof -i :5000-5002")
            return False
        
        if backend_port != 5000:
            print(f"   Port 5000 in use, using port {backend_port} instead")
        
        self.backend_port = backend_port
        
        # Test Flask imports first
        print("   Testing Flask imports...")
        import_success, import_error = self.test_flask_imports()
        if not import_success:
            print("❌ Flask import test failed:")
            print(f"   {import_error}")
            return False
        print("   ✅ Flask imports successful")
        
        try:
            # Set up environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.backend_dir)
            env['FLASK_ENV'] = 'development'
            
            # Start Flask process with dynamic port
            env['FLASK_RUN_PORT'] = str(backend_port)
            self.backend_process = subprocess.Popen(
                [sys.executable, "app.py"],
                cwd=self.backend_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Create queues for real-time output monitoring
            self.output_queue = queue.Queue()
            
            # Start threads to monitor both stdout and stderr
            threading.Thread(
                target=self._read_process_output,
                args=(self.backend_process.stdout, self.output_queue, "STDOUT"),
                daemon=True
            ).start()
            
            threading.Thread(
                target=self._read_process_output,
                args=(self.backend_process.stderr, self.output_queue, "STDERR"),
                daemon=True
            ).start()
            
            # Monitor Flask startup with detailed error capture
            return self._wait_for_flask_startup()
                
        except Exception as e:
            print(f"❌ Error starting backend: {e}")
            return False
    
    def _read_process_output(self, pipe, q, label):
        """Read subprocess output in separate thread"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    q.put((label, line.rstrip()))
            pipe.close()
        except Exception as e:
            q.put((label, f"Error reading {label}: {e}"))
    
    def _wait_for_flask_startup(self, timeout=30):
        """Wait for Flask to start with detailed error monitoring"""
        start_time = time.time()
        flask_started = False
        startup_errors = []
        
        print("   Waiting for Flask to start...")
        
        while time.time() - start_time < timeout:
            # Check if process has terminated early
            if self.backend_process.poll() is not None:
                print(f"❌ Flask process terminated early with code: {self.backend_process.poll()}")
                # Read any remaining output
                self._read_remaining_output(startup_errors)
                return False
            
            # Read output from queue
            try:
                label, line = self.output_queue.get(timeout=1)
                
                # Print all output for debugging
                print(f"   [{label}] {line}")
                
                # Detect Flask startup success
                if "Running on" in line and "http://" in line:
                    flask_started = True
                    print("   ✅ Flask startup detected!")
                    break
                
                # Detect startup errors
                error_indicators = [
                    "ImportError", "ModuleNotFoundError", "SyntaxError",
                    "Address already in use", "Permission denied",
                    "Failed to find application", "Error:", "Exception:",
                    "Traceback", "AttributeError", "NameError"
                ]
                
                if any(error in line for error in error_indicators):
                    startup_errors.append(line)
                
            except queue.Empty:
                continue
        
        # Verify Flask is actually responding with HTTP health check
        if flask_started:
            print("   Verifying Flask is responding...")
            if self._verify_flask_health():
                print(f"✅ Backend server started successfully on http://localhost:{self.backend_port}")
                
                # Start background monitoring for ongoing output
                threading.Thread(
                    target=self._monitor_process_output_enhanced,
                    args=("Backend",),
                    daemon=True
                ).start()
                
                return True
            else:
                print("❌ Flask process started but not responding to HTTP requests")
                startup_errors.append("Flask not responding to HTTP health check")
        
        # Flask failed to start
        print("❌ Flask failed to start within timeout period")
        if startup_errors:
            print("   Detected errors:")
            for error in startup_errors[-5:]:  # Show last 5 errors
                print(f"     - {error}")
        
        # Read any remaining output
        self._read_remaining_output(startup_errors)
        
        # Terminate process if still running
        if self.backend_process.poll() is None:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
        
        return False
    
    def _verify_flask_health(self, max_attempts=5):
        """Verify Flask is responding with HTTP health check"""
        for attempt in range(max_attempts):
            try:
                response = urllib.request.urlopen(f"http://localhost:{self.backend_port}/api/health", timeout=2)
                if response.status == 200:
                    return True
            except Exception:
                time.sleep(1)  # Wait before retry
        return False
    
    def _read_remaining_output(self, startup_errors):
        """Read any remaining output from the queue"""
        remaining_lines = 0
        while remaining_lines < 10:  # Limit to avoid infinite loop
            try:
                label, line = self.output_queue.get(timeout=0.5)
                print(f"   [{label}] {line}")
                startup_errors.append(line)
                remaining_lines += 1
            except queue.Empty:
                break
    
    def _update_frontend_proxy(self):
        """Update the frontend package.json proxy to point to the dynamic backend port"""
        try:
            import json
            package_json_path = self.frontend_dir / "package.json"
            
            # Read current package.json
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Update proxy setting
            new_proxy = f"http://localhost:{self.backend_port}"
            package_data['proxy'] = new_proxy
            
            # Write back to package.json
            with open(package_json_path, 'w') as f:
                json.dump(package_data, f, indent=2)
            
            print(f"   Updated frontend proxy to {new_proxy}")
            
        except Exception as e:
            print(f"   ⚠️ Warning: Could not update frontend proxy: {e}")
            print(f"   Frontend may not be able to communicate with backend on port {self.backend_port}")
    
    def start_frontend(self):
        """Start the React frontend server"""
        print("🚀 Starting React frontend server...")
        
        # Update package.json proxy if backend is not on default port
        if hasattr(self, 'backend_port') and self.backend_port != 5000:
            self._update_frontend_proxy()
        
        try:
            # Set environment variables for React
            env = os.environ.copy()
            env['BROWSER'] = 'none'  # Prevent auto-opening browser
            env['PORT'] = '3000'
            
            self.frontend_process = subprocess.Popen(
                ["npm", "start"],
                cwd=self.frontend_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start thread to monitor frontend output
            threading.Thread(
                target=self._monitor_process_output,
                args=(self.frontend_process, "Frontend"),
                daemon=True
            ).start()
            
            # Wait for frontend to be ready
            print("   Waiting for frontend to start...")
            max_wait = 60  # Maximum wait time in seconds
            wait_time = 0
            
            while wait_time < max_wait:
                if self.frontend_process.poll() is not None:
                    print("❌ Frontend server failed to start")
                    return False
                
                # Check if server is responding
                try:
                    import urllib.request
                    urllib.request.urlopen("http://localhost:3000", timeout=1)
                    print("✅ Frontend server started successfully on http://localhost:3000")
                    return True
                except:
                    time.sleep(2)
                    wait_time += 2
                    print(f"   Still waiting... ({wait_time}s)")
            
            print("❌ Frontend server took too long to start")
            return False
            
        except Exception as e:
            print(f"❌ Error starting frontend: {e}")
            return False
    
    def _monitor_process_output_enhanced(self, name):
        """Enhanced monitoring for ongoing process output"""
        while self.running and self.backend_process.poll() is None:
            try:
                label, line = self.output_queue.get(timeout=1)
                
                # Filter important messages
                if any(keyword in line.lower() for keyword in 
                       ['error', 'failed', 'exception', 'warning', 'critical']):
                    print(f"[{name}] {line}")
                    
            except queue.Empty:
                continue
            except Exception:
                break
    
    def _monitor_process_output(self, process, name):
        """Legacy monitor method for compatibility"""
        while self.running and process.poll() is None:
            try:
                line = process.stdout.readline()
                if line:
                    # Filter out noise and show important messages
                    line = line.strip()
                    if any(keyword in line.lower() for keyword in 
                           ['error', 'failed', 'exception', 'warning', 'started']):
                        print(f"[{name}] {line}")
            except:
                break
    
    def open_browser(self):
        """Open the application in the default browser"""
        print("🌐 Opening application in browser...")
        try:
            webbrowser.open("http://localhost:3000")
            print("✅ Browser opened successfully")
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print("   Please manually open: http://localhost:3000")
    
    def wait_for_shutdown(self):
        """Wait for user to shutdown the application"""
        print()
        print("🎉 RoomieRoster is now running!")
        print()
        print("📍 Application URLs:")
        print("   Frontend: http://localhost:3000")
        print(f"   Backend:  http://localhost:{self.backend_port}")
        print(f"   Health:   http://localhost:{self.backend_port}/api/health")
        print()
        print("💡 Usage:")
        print("   1. Add roommates in the 'Roommates' tab")
        print("   2. Create chores in the 'Chores' tab")
        print("   3. Generate assignments in the 'Assignments' tab")
        print()
        print("⌨️  Press Ctrl+C to stop both servers and exit")
        print("=" * 60)
        
        try:
            while self.running:
                time.sleep(1)
                
                # Check if processes are still running
                if (self.backend_process and self.backend_process.poll() is not None):
                    print("⚠️  Backend server stopped unexpectedly")
                    break
                    
                if (self.frontend_process and self.frontend_process.poll() is not None):
                    print("⚠️  Frontend server stopped unexpectedly")
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
    
    def _restore_frontend_proxy(self):
        """Restore the frontend package.json proxy to the default port 5000"""
        try:
            import json
            package_json_path = self.frontend_dir / "package.json"
            
            # Read current package.json
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Restore original proxy setting
            package_data['proxy'] = "http://localhost:5000"
            
            # Write back to package.json
            with open(package_json_path, 'w') as f:
                json.dump(package_data, f, indent=2)
            
            print("   Restored frontend proxy to default port 5000")
            
        except Exception as e:
            print(f"   ⚠️ Warning: Could not restore frontend proxy: {e}")
    
    def shutdown(self):
        """Gracefully shutdown both servers"""
        self.running = False
        print("🔄 Shutting down servers...")
        
        # Restore frontend proxy if it was modified
        if hasattr(self, 'backend_port') and self.backend_port != 5000:
            self._restore_frontend_proxy()
        
        # Terminate processes
        if self.frontend_process and self.frontend_process.poll() is None:
            print("   Stopping frontend server...")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
                print("   ✅ Frontend server stopped")
            except subprocess.TimeoutExpired:
                print("   🔨 Force killing frontend server...")
                self.frontend_process.kill()
        
        if self.backend_process and self.backend_process.poll() is None:
            print("   Stopping backend server...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
                print("   ✅ Backend server stopped")
            except subprocess.TimeoutExpired:
                print("   🔨 Force killing backend server...")
                self.backend_process.kill()
        
        print("✅ Shutdown complete")
    
    def run(self):
        """Main launcher method"""
        try:
            self.print_banner()
            
            # Check requirements
            if not self.check_requirements():
                print("❌ Requirements check failed. Please fix the issues above.")
                return False
            
            # Install dependencies if needed
            if not self.install_dependencies():
                print("❌ Failed to install dependencies.")
                return False
            
            # Start backend server
            if not self.start_backend():
                print("❌ Failed to start backend server.")
                return False
            
            # Start frontend server
            if not self.start_frontend():
                print("❌ Failed to start frontend server.")
                self.shutdown()
                return False
            
            # Open browser
            self.open_browser()
            
            # Wait for shutdown
            self.wait_for_shutdown()
            
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
        finally:
            self.shutdown()

def main():
    """Main entry point"""
    launcher = RoomieRosterLauncher()
    success = launcher.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()