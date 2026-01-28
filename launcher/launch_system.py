#!/usr/bin/env python3
"""
Collectibles Grading System - Production Launcher
High-end launcher with graphics and sound that starts backend + GUI
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Try to import optional audio libraries
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

try:
    from playsound import playsound
    HAS_PLAYSOUND = True
except ImportError:
    HAS_PLAYSOUND = False


class CollectiblesLauncher:
    """Production-grade launcher for Collectibles Grading System"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.backend_process = None
        self.gui_process = None
        self.backend_ready = False

    def play_startup_sound(self):
        """Play startup sound effect"""
        if HAS_WINSOUND:
            try:
                # Play Windows system sounds as startup sequence
                frequencies = [523, 659, 784, 1047]  # C5, E5, G5, C6
                for freq in frequencies:
                    winsound.Beep(freq, 150)
            except:
                pass
        print("\n" + "=" * 60)
        print("  COLLECTIBLES GRADING SYSTEM - LAUNCHER")
        print("=" * 60 + "\n")

    def play_success_sound(self):
        """Play success sound"""
        if HAS_WINSOUND:
            try:
                winsound.Beep(784, 100)
                winsound.Beep(988, 100)
                winsound.Beep(1319, 200)
            except:
                pass

    def play_error_sound(self):
        """Play error sound"""
        if HAS_WINSOUND:
            try:
                winsound.Beep(200, 500)
            except:
                pass

    def print_banner(self):
        """Print ASCII art banner"""
        banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗ ██████╗ ██╗     ██╗     ███████╗ ██████╗████████╗   ║
    ║  ██╔════╝██╔═══██╗██║     ██║     ██╔════╝██╔════╝╚══██╔══╝   ║
    ║  ██║     ██║   ██║██║     ██║     █████╗  ██║        ██║      ║
    ║  ██║     ██║   ██║██║     ██║     ██╔══╝  ██║        ██║      ║
    ║  ╚██████╗╚██████╔╝███████╗███████╗███████╗╚██████╗   ██║      ║
    ║   ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝ ╚═════╝   ╚═╝      ║
    ║                                                               ║
    ║              GRADING SYSTEM v2.0                              ║
    ║         AI-Powered Collectibles Analysis                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def print_status(self, message, status="INFO"):
        """Print formatted status message"""
        colors = {
            "INFO": "\033[36m",     # Cyan
            "SUCCESS": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
            "RESET": "\033[0m"
        }

        color = colors.get(status, colors["INFO"])
        reset = colors["RESET"]
        timestamp = time.strftime("%H:%M:%S")

        print(f"{color}[{timestamp}] [{status:^8}]{reset} {message}")

    def check_dependencies(self):
        """Check if all dependencies are available"""
        self.print_status("Checking system dependencies...", "INFO")

        checks = [
            ("Python", sys.executable),
            ("Backend", self.project_root / "backend" / "main.py"),
            ("Electron", self.project_root / "electron-app" / "main.js"),
            ("Database", self.project_root / "collectibles.db"),
        ]

        all_good = True
        for name, path in checks:
            if isinstance(path, Path):
                exists = path.exists()
            else:
                exists = True

            if exists:
                self.print_status(f"  ✓ {name} found", "SUCCESS")
            else:
                self.print_status(f"  ✗ {name} not found: {path}", "ERROR")
                all_good = False

        return all_good

    def start_backend(self):
        """Start the FastAPI backend server"""
        self.print_status("Starting FastAPI backend server...", "INFO")

        backend_dir = self.project_root / "backend"
        main_py = backend_dir / "main.py"

        if not main_py.exists():
            self.print_status("Backend main.py not found!", "ERROR")
            return False

        try:
            # Start backend in subprocess
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)

            self.backend_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                cwd=str(backend_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )

            self.print_status("Backend server starting on http://localhost:8000", "SUCCESS")
            return True

        except Exception as e:
            self.print_status(f"Failed to start backend: {e}", "ERROR")
            return False

    def wait_for_backend(self, timeout=30):
        """Wait for backend to be ready"""
        import urllib.request
        import urllib.error

        self.print_status("Waiting for backend to be ready...", "INFO")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = urllib.request.urlopen("http://localhost:8000/health", timeout=2)
                if response.status == 200:
                    self.backend_ready = True
                    self.print_status("Backend is ready!", "SUCCESS")
                    return True
            except (urllib.error.URLError, ConnectionRefusedError):
                pass
            except Exception:
                pass

            time.sleep(1)
            print(".", end="", flush=True)

        print()
        self.print_status("Backend failed to start within timeout", "WARNING")
        return False

    def start_gui(self):
        """Start the Electron GUI"""
        self.print_status("Starting Electron GUI...", "INFO")

        electron_dir = self.project_root / "electron-app"

        if not (electron_dir / "main.js").exists():
            self.print_status("Electron app not found!", "ERROR")
            return False

        try:
            # Check if npm/electron is available
            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

            self.gui_process = subprocess.Popen(
                [npm_cmd, "start"],
                cwd=str(electron_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )

            self.print_status("Electron GUI starting...", "SUCCESS")
            return True

        except FileNotFoundError:
            self.print_status("npm not found - trying electron directly...", "WARNING")

            try:
                electron_cmd = str(electron_dir / "node_modules" / ".bin" / "electron")
                if sys.platform == "win32":
                    electron_cmd += ".cmd"

                self.gui_process = subprocess.Popen(
                    [electron_cmd, "."],
                    cwd=str(electron_dir),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
                )
                self.print_status("Electron GUI starting via direct call...", "SUCCESS")
                return True

            except Exception as e:
                self.print_status(f"Failed to start GUI: {e}", "ERROR")
                return False

        except Exception as e:
            self.print_status(f"Failed to start GUI: {e}", "ERROR")
            return False

    def open_web_launcher(self):
        """Open the HTML launcher in default browser"""
        launcher_html = self.project_root / "launcher" / "launcher.html"
        if launcher_html.exists():
            webbrowser.open(f"file://{launcher_html}")
            self.print_status("Opened web launcher in browser", "SUCCESS")

    def launch(self):
        """Main launch sequence"""
        self.play_startup_sound()
        self.print_banner()

        # Check dependencies
        if not self.check_dependencies():
            self.print_status("Dependency check failed!", "ERROR")
            self.play_error_sound()
            return False

        print()

        # Start backend
        if not self.start_backend():
            self.play_error_sound()
            return False

        # Wait for backend
        time.sleep(2)  # Give it a moment to start
        self.wait_for_backend(timeout=30)

        print()

        # Start GUI
        if not self.start_gui():
            self.print_status("GUI failed to start, but backend is running", "WARNING")

        self.play_success_sound()

        print()
        print("=" * 60)
        self.print_status("SYSTEM LAUNCH COMPLETE", "SUCCESS")
        print("=" * 60)
        print()
        self.print_status("Backend API: http://localhost:8000", "INFO")
        self.print_status("API Docs: http://localhost:8000/docs", "INFO")
        self.print_status("Press Ctrl+C to stop all services", "INFO")
        print()

        return True

    def shutdown(self):
        """Shutdown all services"""
        self.print_status("Shutting down services...", "INFO")

        if self.backend_process:
            self.backend_process.terminate()
            self.print_status("Backend stopped", "SUCCESS")

        if self.gui_process:
            self.gui_process.terminate()
            self.print_status("GUI stopped", "SUCCESS")

    def run(self):
        """Run the launcher with graceful shutdown"""
        try:
            if self.launch():
                # Keep running until interrupted
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print()
            self.shutdown()
            self.print_status("Goodbye!", "INFO")


def main():
    """Entry point"""
    launcher = CollectiblesLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
