"""
FocusFlow - Unified Application Launcher

This script starts all required services for the FocusFlow application:
1. Backend API (FastAPI/Uvicorn)
2. Frontend Server (HTTP Server for static files)
3. Database connection check

Usage:
    python run.py                    # Start all services
    python run.py --backend-only     # Start only backend
    python run.py --frontend-only    # Start only frontend
    python run.py --port 8000        # Custom backend port
"""

import subprocess
import sys
import os
import time
import signal
import argparse
from pathlib import Path
import webbrowser
from threading import Thread

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Configuration
BACKEND_PORT = 8000
FRONTEND_PORT = 3000
BACKEND_DIR = Path(__file__).parent / "backend"
FRONTEND_DIR = Path(__file__).parent / "frontend"

# Global process list
processes = []


def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def check_python_version():
    """Check if Python version is compatible"""
    print_info("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ required. Current version: {version.major}.{version.minor}")
        sys.exit(1)
    print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")


def check_dependencies():
    """Check if required dependencies are installed"""
    print_info("Checking backend dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'mysql.connector',
        'pydantic',
        'tensorflow',
        'opencv-python',
        'mediapipe'
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'opencv-python':
                __import__('cv2')
            elif package == 'mysql.connector':
                __import__('mysql.connector')
            else:
                __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print_warning(f"Missing packages: {', '.join(missing)}")
        print_info("Install with: pip install -r backend/requirements.txt")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            sys.exit(1)
    else:
        print_success("All backend dependencies installed ✓")


def check_database_connection():
    """Check if database is accessible"""
    print_info("Checking database connection...")
    
    try:
        # Add backend to path to import database module
        sys.path.insert(0, str(BACKEND_DIR))
        from database import db
        
        if db.test_connection():
            print_success("Database connection successful ✓")
            return True
        else:
            print_warning("Database connection failed")
            print_info("Make sure MySQL is running and credentials are correct")
            response = input("Continue without database? (y/n): ").lower()
            return response == 'y'
    except Exception as e:
        print_warning(f"Database check failed: {e}")
        print_info("Backend will start but may not function properly")
        response = input("Continue anyway? (y/n): ").lower()
        return response == 'y'


def check_ml_models():
    """Check if ML models are present"""
    print_info("Checking ML models...")
    
    models = [
        BACKEND_DIR / "models" / "face_detection" / "detect_face.tflite",
        BACKEND_DIR / "models" / "eye_tracking" / "track_eye.task",
        BACKEND_DIR / "models" / "emotion_detection" / "detect_emotion.h5"
    ]
    
    missing = []
    for model in models:
        if not model.exists():
            missing.append(model.name)
    
    if missing:
        print_warning(f"Missing ML models: {', '.join(missing)}")
        print_info("Computer vision features will be disabled")
        print_info("See backend/models/README.md for download instructions")
    else:
        print_success("All ML models present ✓")


def start_backend(port=BACKEND_PORT):
    """Start the backend API server"""
    print_header("Starting Backend Server")
    
    print_info(f"Backend directory: {BACKEND_DIR}")
    print_info(f"Backend port: {port}")
    
    try:
        # Start uvicorn server
        cmd = [
            sys.executable,
            "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload"
        ]
        
        # On Windows, don't pipe output to avoid blocking issues
        # Create process in new console or detached
        if sys.platform == "win32":
            process = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR)
            )
        
        processes.append(("Backend", process))
        
        # Wait for backend to start
        print_info("Waiting for backend to start...")
        time.sleep(4)
        
        # Verify it's running
        if process.poll() is None:
            print_success(f"Backend started successfully on http://localhost:{port}")
            print_info(f"API docs: http://localhost:{port}/docs")
            print_info(f"Health check: http://localhost:{port}/health")
            return process
        else:
            print_error("Backend failed to start")
            return None
            
    except Exception as e:
        print_error(f"Failed to start backend: {e}")
        return None


def start_frontend(port=FRONTEND_PORT):
    """Start the frontend HTTP server"""
    print_header("Starting Frontend Server")
    
    print_info(f"Frontend directory: {FRONTEND_DIR}")
    print_info(f"Frontend port: {port}")
    
    try:
        # Start simple HTTP server for static files
        cmd = [
            sys.executable,
            "-m", "http.server",
            str(port),
            "--directory", str(FRONTEND_DIR)
        ]
        
        # On Windows, create process in new console
        if sys.platform == "win32":
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(cmd)
        
        processes.append(("Frontend", process))
        
        # Wait for frontend to start
        print_info("Waiting for frontend to start...")
        time.sleep(2)
        
        # Verify it's running
        if process.poll() is None:
            print_success(f"Frontend started successfully on http://localhost:{port}")
            print_info(f"Application URL: http://localhost:{port}")
            return process
        else:
            print_error("Frontend failed to start")
            return None
            
    except Exception as e:
        print_error(f"Failed to start frontend: {e}")
        return None


def monitor_process(name, process):
    """Monitor a process and print its output"""
    try:
        for line in process.stdout:
            if line.strip():
                # Filter out excessive logging
                if "GET /" not in line and "POST /" not in line:
                    print(f"[{name}] {line.strip()}")
    except Exception:
        pass


def open_browser(url, delay=2):
    """Open browser after a delay"""
    time.sleep(delay)
    try:
        print_header("Opening Browser")
        print_success(f"🌐 Opening {url} in your default browser...")
        webbrowser.open(url)
        print_success(f"✓ Browser opened successfully!")
    except Exception as e:
        print_warning(f"Could not open browser automatically: {e}")
        print_info(f"Please manually open: {url}")


def cleanup():
    """Cleanup all running processes"""
    print_header("Shutting Down")
    
    for name, process in processes:
        if process and process.poll() is None:
            print_info(f"Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=5)
                print_success(f"{name} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                print_warning(f"{name} force killed")
            except Exception as e:
                print_error(f"Error stopping {name}: {e}")
    
    print_success("All services stopped")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n")
    cleanup()
    sys.exit(0)


def main():
    """Main entry point"""
    # Parse arguments
    parser = argparse.ArgumentParser(description="FocusFlow Application Launcher")
    parser.add_argument("--backend-only", action="store_true", help="Start only backend")
    parser.add_argument("--frontend-only", action="store_true", help="Start only frontend")
    parser.add_argument("--port", type=int, default=BACKEND_PORT, help="Backend port")
    parser.add_argument("--frontend-port", type=int, default=FRONTEND_PORT, help="Frontend port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency checks")
    
    args = parser.parse_args()
    
    # Print header
    print_header("FocusFlow Application Launcher")
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run checks
        if not args.skip_checks:
            check_python_version()
            check_dependencies()
            
            if not args.frontend_only:
                db_ok = check_database_connection()
                if not db_ok:
                    print_error("Cannot start without database")
                    sys.exit(1)
                check_ml_models()
        
        # Start services
        backend_process = None
        frontend_process = None
        
        if not args.frontend_only:
            backend_process = start_backend(args.port)
            if not backend_process:
                print_error("Failed to start backend")
                sys.exit(1)
        
        if not args.backend_only:
            frontend_process = start_frontend(args.frontend_port)
            if not frontend_process:
                print_error("Failed to start frontend")
                if backend_process:
                    cleanup()
                sys.exit(1)
        
        # Print status
        print_header("Services Running")
        
        if backend_process:
            print_success(f"Backend:  http://localhost:{args.port}")
            print_info(f"          http://localhost:{args.port}/docs (API Docs)")
        
        if frontend_process:
            print_success(f"Frontend: http://localhost:{args.frontend_port}")
        
        print("\n")
        print_info("Press Ctrl+C to stop all services")
        
        # Open browser notification
        if not args.no_browser and frontend_process:
            print("\n")
            print_success("🌐 Browser will open automatically in 2 seconds...")
            print_info(f"   Opening: http://localhost:{args.frontend_port}")
        
        print("\n")
        
        # Open browser
        if not args.no_browser and frontend_process:
            Thread(target=open_browser, args=(f"http://localhost:{args.frontend_port}",), daemon=True).start()
        
        # Keep running until interrupted
        # Processes are running in separate consoles on Windows
        print_info("Services are running. Check the separate console windows for logs.")
        print_info("To stop all services, close this window or press Ctrl+C")
        print("\n")
        
        while True:
            time.sleep(5)
            
            # Check if processes are still running
            if backend_process and backend_process.poll() is not None:
                print_error("Backend process stopped unexpectedly")
                break
            
            if frontend_process and frontend_process.poll() is not None:
                print_error("Frontend process stopped unexpectedly")
                break
    
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print_error(f"Unexpected error: {e}")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
