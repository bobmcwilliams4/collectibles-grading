#!/usr/bin/env python3
"""
EPOCGS Desktop App - Installer Build Script
Creates distributable packages for Windows, macOS, and Linux

Usage:
    python scripts/build_installers.py --platform windows
    python scripts/build_installers.py --platform macos
    python scripts/build_installers.py --platform linux
    python scripts/build_installers.py --platform all

Requirements:
    - PyInstaller: pip install pyinstaller
    - NSIS (Windows): https://nsis.sourceforge.io/Download
    - create-dmg (macOS): brew install create-dmg
    - fpm (Linux): gem install fpm
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# ========== CONFIGURATION ==========

APP_NAME = "EPOCGS"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Echo Prime Omega Collectibles Grading System"
APP_AUTHOR = "ECHO PRIME"
APP_URL = "https://echo-op.com/downloads/epocgs"

PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLERS_DIR = PROJECT_ROOT / "installers"

# ========== COLORS ==========

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

def print_step(message: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}→ {message}{Colors.ENDC}")

def print_success(message: str):
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_error(message: str):
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_warning(message: str):
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

# ========== BUILD FUNCTIONS ==========

def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        return False

def clean_build_dirs():
    """Clean previous build artifacts"""
    print_step("Cleaning previous build artifacts...")

    dirs_to_clean = [BUILD_DIR, DIST_DIR, INSTALLERS_DIR]
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print_success(f"Cleaned {dir_path}")

    INSTALLERS_DIR.mkdir(parents=True, exist_ok=True)
    print_success("Build directories ready")

def build_with_pyinstaller():
    """Build executable with PyInstaller"""
    print_step("Building executable with PyInstaller...")

    # Check if spec file exists
    spec_file = PROJECT_ROOT / "epocgs.spec"
    if not spec_file.exists():
        print_error("epocgs.spec file not found!")
        return False

    # Run PyInstaller
    cmd = ["pyinstaller", "--clean", str(spec_file)]
    if run_command(cmd):
        print_success("PyInstaller build completed")
        return True
    else:
        print_error("PyInstaller build failed")
        return False

def build_windows_installer():
    """Build Windows installer with NSIS"""
    print_step("Building Windows installer (.exe)...")

    # Check for NSIS
    nsis_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]

    makensis = None
    for path in nsis_paths:
        if Path(path).exists():
            makensis = path
            break

    if not makensis:
        print_warning("NSIS not found. Skipping Windows installer creation.")
        print_warning("Download from: https://nsis.sourceforge.io/Download")
        return False

    # Create NSIS script
    nsis_script = create_nsis_script()
    nsis_file = PROJECT_ROOT / "installer.nsi"
    nsis_file.write_text(nsis_script)

    # Run NSIS
    cmd = [makensis, "/V4", str(nsis_file)]
    if run_command(cmd):
        print_success("Windows installer created")
        return True
    else:
        print_error("Windows installer creation failed")
        return False

def create_nsis_script() -> str:
    """Generate NSIS installer script"""
    return f"""
!define APP_NAME "{APP_NAME}"
!define APP_VERSION "{APP_VERSION}"
!define APP_PUBLISHER "{APP_AUTHOR}"
!define APP_URL "{APP_URL}"
!define APP_EXE "EPOCGS.exe"

Name "${{APP_NAME}}"
OutFile "installers\\${{APP_NAME}}-${{APP_VERSION}}-Windows-Setup.exe"
InstallDir "$PROGRAMFILES64\\${{APP_NAME}}"
InstallDirRegKey HKLM "Software\\${{APP_NAME}}" "Install_Dir"
RequestExecutionLevel admin

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "images\\icon.ico"
!define MUI_UNICON "images\\icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\\EPOCGS\\*.*"

  WriteRegStr HKLM "Software\\${{APP_NAME}}" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayName" "${{APP_NAME}}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "UninstallString" '"$INSTDIR\\uninstall.exe"'
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoModify" 1
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoRepair" 1
  WriteUninstaller "$INSTDIR\\uninstall.exe"

  CreateDirectory "$SMPROGRAMS\\${{APP_NAME}}"
  CreateShortcut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXE}}"
  CreateShortcut "$DESKTOP\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXE}}"
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\\uninstall.exe"
  Delete "$DESKTOP\\${{APP_NAME}}.lnk"
  Delete "$SMPROGRAMS\\${{APP_NAME}}\\*.*"
  RMDir "$SMPROGRAMS\\${{APP_NAME}}"
  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}"
  DeleteRegKey HKLM "Software\\${{APP_NAME}}"
SectionEnd
"""

def build_macos_dmg():
    """Build macOS DMG installer"""
    print_step("Building macOS DMG installer...")

    # Check for create-dmg
    if shutil.which("create-dmg") is None:
        print_warning("create-dmg not found. Skipping macOS DMG creation.")
        print_warning("Install with: brew install create-dmg")
        return False

    app_bundle = DIST_DIR / "EPOCGS.app"
    if not app_bundle.exists():
        print_error("EPOCGS.app not found in dist/")
        return False

    dmg_file = INSTALLERS_DIR / f"{APP_NAME}-{APP_VERSION}-macOS.dmg"

    cmd = [
        "create-dmg",
        "--volname", APP_NAME,
        "--volicon", "images/icon.icns",
        "--window-pos", "200", "120",
        "--window-size", "800", "400",
        "--icon-size", "100",
        "--icon", "EPOCGS.app", "200", "190",
        "--hide-extension", "EPOCGS.app",
        "--app-drop-link", "600", "185",
        str(dmg_file),
        str(app_bundle),
    ]

    if run_command(cmd):
        print_success(f"macOS DMG created: {dmg_file}")
        return True
    else:
        print_error("macOS DMG creation failed")
        return False

def build_linux_packages():
    """Build Linux packages (.deb, .rpm, .AppImage)"""
    print_step("Building Linux packages...")

    # Check for fpm
    if shutil.which("fpm") is None:
        print_warning("fpm not found. Skipping Linux package creation.")
        print_warning("Install with: gem install fpm")
        return False

    exe_dir = DIST_DIR / "EPOCGS"
    if not exe_dir.exists():
        print_error("EPOCGS executable directory not found in dist/")
        return False

    # Create .deb package
    deb_file = INSTALLERS_DIR / f"{APP_NAME.lower()}_{APP_VERSION}_amd64.deb"
    cmd_deb = [
        "fpm",
        "-s", "dir",
        "-t", "deb",
        "-n", APP_NAME.lower(),
        "-v", APP_VERSION,
        "--description", APP_DESCRIPTION,
        "--url", APP_URL,
        "--maintainer", APP_AUTHOR,
        "--license", "Proprietary",
        "-C", str(exe_dir),
        "-p", str(deb_file),
        ".",
    ]

    # Create .rpm package
    rpm_file = INSTALLERS_DIR / f"{APP_NAME.lower()}-{APP_VERSION}-1.x86_64.rpm"
    cmd_rpm = cmd_deb.copy()
    cmd_rpm[cmd_rpm.index("-t") + 1] = "rpm"
    cmd_rpm[cmd_rpm.index("-p") + 1] = str(rpm_file)

    success = True
    if run_command(cmd_deb):
        print_success(f"Debian package created: {deb_file}")
    else:
        print_error("Debian package creation failed")
        success = False

    if run_command(cmd_rpm):
        print_success(f"RPM package created: {rpm_file}")
    else:
        print_error("RPM package creation failed")
        success = False

    return success

def create_portable_zip():
    """Create portable ZIP archive"""
    print_step("Creating portable ZIP archive...")

    exe_dir = DIST_DIR / "EPOCGS"
    if not exe_dir.exists():
        print_error("EPOCGS executable directory not found")
        return False

    import zipfile

    current_platform = platform.system()
    zip_file = INSTALLERS_DIR / f"{APP_NAME}-{APP_VERSION}-{current_platform}-Portable.zip"

    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in exe_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(exe_dir.parent)
                zipf.write(file, arcname)

    print_success(f"Portable ZIP created: {zip_file}")
    return True

# ========== MAIN ==========

def main():
    parser = argparse.ArgumentParser(description="Build EPOCGS installers")
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux", "all"],
        default="all",
        help="Target platform(s)",
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Skip cleaning build directories",
    )
    args = parser.parse_args()

    print(f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║              EPOCGS INSTALLER BUILD SCRIPT                   ║
║              Version {APP_VERSION}                                      ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}
""")

    # Clean build directories
    if not args.skip_clean:
        clean_build_dirs()

    # Build with PyInstaller
    if not build_with_pyinstaller():
        print_error("Build failed!")
        sys.exit(1)

    # Create portable ZIP for all platforms
    create_portable_zip()

    # Platform-specific installers
    current_platform = platform.system()

    if args.platform in ["windows", "all"] and current_platform == "Windows":
        build_windows_installer()

    if args.platform in ["macos", "all"] and current_platform == "Darwin":
        build_macos_dmg()

    if args.platform in ["linux", "all"] and current_platform == "Linux":
        build_linux_packages()

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Build complete!{Colors.ENDC}")
    print(f"\nInstallers created in: {INSTALLERS_DIR}")
    print("\nFiles:")
    for file in INSTALLERS_DIR.glob("*"):
        file_size = file.stat().st_size / (1024 * 1024)  # MB
        print(f"  • {file.name} ({file_size:.1f} MB)")

if __name__ == "__main__":
    main()
