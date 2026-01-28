# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for EPOCGS Desktop App
Packages the app for Windows, macOS, and Linux
"""

block_cipher = None

import sys
from pathlib import Path

# Get the application directory
app_dir = Path('.').resolve()

# Collect all backend files
backend_files = []
for ext in ['*.py', '*.json', '*.txt', '*.md']:
    for file in (app_dir / 'backend').rglob(ext):
        backend_files.append((str(file), str(file.relative_to(app_dir).parent)))

# Collect config files
config_files = []
for file in (app_dir / 'config').glob('*'):
    if file.is_file():
        config_files.append((str(file), 'config'))

# Collect templates
template_files = []
for file in (app_dir / 'templates').glob('*'):
    if file.is_file():
        template_files.append((str(file), 'templates'))

# Collect static assets
static_files = []
for file in (app_dir / 'static_export').rglob('*'):
    if file.is_file():
        static_files.append((str(file), str(file.relative_to(app_dir).parent)))

# All data files
datas = backend_files + config_files + template_files + static_files + [
    ('README.md', '.'),
    ('requirements.txt', '.'),
]

# Hidden imports (packages that PyInstaller might miss)
hiddenimports = [
    'anthropic',
    'google.generativeai',
    'openai',
    'fastapi',
    'uvicorn',
    'pydantic',
    'pydantic_settings',
    'cv2',
    'PIL',
    'numpy',
    'sqlite3',
    'aiosqlite',
    'httpx',
    'websockets',
    'jinja2',
    'structlog',
    'python_dateutil',
    'pytz',
    'colorama',
    'tenacity',
    'cachetools',
    'cryptography',
    'jose',
    'passlib',
    'dotenv',
    'pyttsx3',
]

a = Analysis(
    ['backend/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'sklearn',
        'IPython',
        'notebook',
        'jupyter',
        'tkinter',
        'PyQt5',
        'PyQt6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EPOCGS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for windowed app
    disable_windowing=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/icon.ico' if sys.platform == 'win32' else 'images/icon.icns',
)

# Create macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='EPOCGS.app',
        icon='images/icon.icns',
        bundle_identifier='com.echoprime.epocgs',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'EPOCGS Project',
                    'CFBundleTypeRole': 'Editor',
                    'LSItemContentTypes': ['com.echoprime.epocgs.project'],
                }
            ]
        },
    )
