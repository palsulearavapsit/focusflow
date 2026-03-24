"""
FocusFlow - Unified Application Launcher

Usage:
    python run.py                  # Start backend + frontend + open browser
    python run.py --backend-only   # Start only backend
    python run.py --frontend-only  # Start only frontend
    python run.py --no-browser     # Don't auto-open browser
    python run.py --skip-checks    # Skip dependency/DB checks
"""

import subprocess
import sys
import os
import time
import signal
import argparse
from pathlib import Path
from threading import Thread
import webbrowser

# ─── ANSI Colors ──────────────────────────────────────────────────────────────
class C:
    BOLD   = '\033[1m'
    GREEN  = '\033[92m'
    CYAN   = '\033[96m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    PURPLE = '\033[95m'
    RESET  = '\033[0m'

# ─── Config ───────────────────────────────────────────────────────────────────
BACKEND_PORT   = 8000
FRONTEND_PORT  = 3000
ROOT_DIR       = Path(__file__).parent
BACKEND_DIR    = ROOT_DIR / "backend"
FRONTEND_DIR   = ROOT_DIR / "frontend"

processes = []

# ─── Print Helpers ────────────────────────────────────────────────────────────
def banner(text):
    print(f"\n{C.PURPLE}{C.BOLD}{'─' * 58}{C.RESET}")
    print(f"{C.PURPLE}{C.BOLD}  {text}{C.RESET}")
    print(f"{C.PURPLE}{C.BOLD}{'─' * 58}{C.RESET}\n")

def ok(text):   print(f"  {C.GREEN}✓  {text}{C.RESET}")
def info(text): print(f"  {C.CYAN}ℹ  {text}{C.RESET}")
def warn(text): print(f"  {C.YELLOW}⚠  {text}{C.RESET}")
def err(text):  print(f"  {C.RED}✗  {text}{C.RESET}")

# ─── Checks ───────────────────────────────────────────────────────────────────
def check_python():
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        err(f"Python 3.8+ required. Got {v.major}.{v.minor}")
        sys.exit(1)
    ok(f"Python {v.major}.{v.minor}.{v.micro}")


def check_dependencies():
    info("Checking dependencies...")
    required = {
        'fastapi':              'fastapi',
        'uvicorn':              'uvicorn',
        'mysql.connector':      'mysql-connector-python',
        'pydantic':             'pydantic',
        'jose':                 'python-jose',
        'passlib':              'passlib',
    }
    missing = []
    for module, pkg in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)

    if missing:
        warn(f"Missing packages: {', '.join(missing)}")
        info("Run: pip install -r backend/requirements.txt")
        ans = input("  Continue anyway? (y/n): ").strip().lower()
        if ans != 'y':
            sys.exit(1)
    else:
        ok("All core dependencies installed")

    # Optional ML check (non-blocking)
    ml_ok = []
    for mod in ['cv2', 'mediapipe', 'tensorflow']:
        try:
            __import__(mod)
            ml_ok.append(mod)
        except ImportError:
            pass
    if ml_ok:
        ok(f"ML packages available: {', '.join(ml_ok)}")
    else:
        warn("ML packages (tensorflow/mediapipe/opencv) not found — camera features disabled")


def check_database():
    info("Testing MySQL connection...")
    try:
        sys.path.insert(0, str(BACKEND_DIR))
        from database import db
        if db.test_connection():
            ok("MySQL connected ✓")
            return True
        else:
            warn("MySQL connection failed")
            info("Check DB_HOST / DB_USER / DB_PASSWORD / DB_NAME in backend/.env")
            ans = input("  Continue without DB? (y/n): ").strip().lower()
            return ans == 'y'
    except Exception as e:
        warn(f"DB check error: {e}")
        ans = input("  Continue anyway? (y/n): ").strip().lower()
        return ans == 'y'


def check_ml_models():
    model_dir = BACKEND_DIR / "models"
    models = [
        ("detect_face.tflite",  "Face Detection"),
        ("track_eye.task",      "Eye Tracking"),
        ("emotion_model.h5",    "Emotion Detection"),
    ]
    missing = [name for fname, name in models if not (model_dir / fname).exists()]
    if missing:
        warn(f"ML models missing: {', '.join(missing)}")
        info("Camera-based features will be limited to OpenCV fallback")
    else:
        ok("All ML models found")


# ─── Service Starters ─────────────────────────────────────────────────────────
def start_backend(port=BACKEND_PORT):
    banner("Starting Backend  (FastAPI + MySQL)")

    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload"
    ]

    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            proc = subprocess.Popen(cmd, cwd=str(BACKEND_DIR))

        processes.append(("Backend", proc))
        info("Waiting for backend to start...")
        time.sleep(4)

        if proc.poll() is None:
            ok(f"Backend running  →  http://localhost:{port}")
            info(f"API Docs         →  http://localhost:{port}/docs")
            info(f"Health check     →  http://localhost:{port}/health")
            return proc
        else:
            err("Backend failed to start — check the console window")
            return None
    except Exception as e:
        err(f"Failed to start backend: {e}")
        return None


def start_frontend(port=FRONTEND_PORT):
    banner("Starting Frontend  (Static HTTP Server)")

    cmd = [
        sys.executable, "-m", "http.server",
        str(port),
        "--directory", str(FRONTEND_DIR)
    ]

    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            proc = subprocess.Popen(cmd)

        processes.append(("Frontend", proc))
        info("Waiting for frontend to start...")
        time.sleep(2)

        if proc.poll() is None:
            ok(f"Frontend running →  http://localhost:{port}")
            return proc
        else:
            err("Frontend failed to start")
            return None
    except Exception as e:
        err(f"Failed to start frontend: {e}")
        return None


# ─── Browser ─────────────────────────────────────────────────────────────────
def open_browser(url, delay=3):
    time.sleep(delay)
    try:
        webbrowser.open(url)
        ok(f"Browser opened → {url}")
    except Exception:
        warn(f"Could not auto-open browser. Visit: {url}")


# ─── Cleanup ─────────────────────────────────────────────────────────────────
def cleanup():
    banner("Shutting Down")
    for name, proc in processes:
        if proc and proc.poll() is None:
            info(f"Stopping {name}...")
            try:
                proc.terminate()
                proc.wait(timeout=5)
                ok(f"{name} stopped")
            except subprocess.TimeoutExpired:
                proc.kill()
                warn(f"{name} force-killed")
            except Exception as e:
                err(f"Error stopping {name}: {e}")
    ok("All services stopped. Goodbye!")


def signal_handler(signum, frame):
    print("\n")
    cleanup()
    sys.exit(0)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="FocusFlow Launcher")
    parser.add_argument("--backend-only",  action="store_true")
    parser.add_argument("--frontend-only", action="store_true")
    parser.add_argument("--no-browser",    action="store_true")
    parser.add_argument("--skip-checks",   action="store_true")
    parser.add_argument("--port",          type=int, default=BACKEND_PORT)
    parser.add_argument("--frontend-port", type=int, default=FRONTEND_PORT)
    args = parser.parse_args()

    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ── Header ────────────────────────────────────────────────────────────────
    banner("🎯  FocusFlow Launcher")
    # ── Checks ────────────────────────────────────────────────────────────────
    if not args.skip_checks:
        banner("Pre-flight Checks")
        check_python()
        check_dependencies()

        if not args.frontend_only:
            if not check_database():
                err("Cannot start without database. Exiting.")
                sys.exit(1)
            check_ml_models()

    # ── Start Services ────────────────────────────────────────────────────────
    backend_proc  = None
    frontend_proc = None

    if not args.frontend_only:
        backend_proc = start_backend(args.port)
        if not backend_proc:
            err("Backend failed. Exiting.")
            sys.exit(1)

    if not args.backend_only:
        frontend_proc = start_frontend(args.frontend_port)
        if not frontend_proc:
            err("Frontend failed. Exiting.")
            cleanup()
            sys.exit(1)

    # ── Summary ───────────────────────────────────────────────────────────────
    banner("🚀  FocusFlow is Running!")
    if backend_proc:
        ok(f"Backend   →  http://localhost:{args.port}")
        info(f"API Docs  →  http://localhost:{args.port}/docs")
    if frontend_proc:
        ok(f"Frontend  →  http://localhost:{args.frontend_port}")

    print(f"\n  {C.YELLOW}Press Ctrl+C to stop all services{C.RESET}\n")

    # ── Open Browser ─────────────────────────────────────────────────────────
    if not args.no_browser and frontend_proc:
        Thread(
            target=open_browser,
            args=(f"http://localhost:{args.frontend_port}",),
            daemon=True
        ).start()

    # ── Keep Alive ────────────────────────────────────────────────────────────
    try:
        while True:
            time.sleep(5)
            if backend_proc  and backend_proc.poll()  is not None:
                err("Backend stopped unexpectedly!")
                break
            if frontend_proc and frontend_proc.poll() is not None:
                err("Frontend stopped unexpectedly!")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
