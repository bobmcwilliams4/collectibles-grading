# EPOCGS Desktop App - Build & Distribution Guide

**Version**: 1.0.0
**Platform**: Windows, macOS, Linux
**Updated**: 2026-01-06

---

## 📦 OVERVIEW

This guide covers building distributable packages for the EPOCGS desktop application across all three major platforms:
- **Windows**: `.exe` installer (NSIS)
- **macOS**: `.dmg` disk image
- **Linux**: `.deb`, `.rpm`, and `.AppImage` packages
- **All Platforms**: Portable ZIP archives

---

## 🔧 PREREQUISITES

### All Platforms

```bash
# Python 3.11+
python --version

# PyInstaller
pip install pyinstaller

# Build dependencies
pip install -r requirements.txt
```

### Windows-Specific

**NSIS Installer:**
- Download: https://nsis.sourceforge.io/Download
- Install to default location: `C:\Program Files (x86)\NSIS\`

### macOS-Specific

**create-dmg Tool:**
```bash
brew install create-dmg
```

**Xcode Command Line Tools:**
```bash
xcode-select --install
```

### Linux-Specific

**fpm (Effing Package Management):**
```bash
# Install Ruby first
sudo apt install ruby ruby-dev rubygems build-essential

# Install fpm
gem install --no-document fpm
```

**Additional tools:**
```bash
# Debian/Ubuntu
sudo apt install rpm dpkg-deb

# Fedora/RHEL
sudo dnf install rpm-build alien
```

---

## 🏗️ BUILD PROCESS

### Quick Build (Recommended)

```bash
cd P:/SOVEREIGN_APPS/collectibles_grading_system

# Build for current platform
python scripts/build_installers.py

# Build for specific platform
python scripts/build_installers.py --platform windows
python scripts/build_installers.py --platform macos
python scripts/build_installers.py --platform linux
```

### Manual Build Steps

#### Step 1: Clean Previous Builds

```bash
rm -rf build/ dist/ installers/
```

#### Step 2: Build with PyInstaller

```bash
pyinstaller --clean epocgs.spec
```

**What this does:**
- Analyzes dependencies
- Bundles Python interpreter
- Packages all backend files
- Creates standalone executable in `dist/EPOCGS/`

#### Step 3: Platform-Specific Packaging

**Windows (.exe installer):**
```bash
makensis /V4 installer.nsi
```

**macOS (.dmg):**
```bash
create-dmg \
  --volname "EPOCGS" \
  --volicon "images/icon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "EPOCGS.app" 200 190 \
  --hide-extension "EPOCGS.app" \
  --app-drop-link 600 185 \
  "installers/EPOCGS-1.0.0-macOS.dmg" \
  "dist/EPOCGS.app"
```

**Linux (.deb):**
```bash
fpm -s dir -t deb \
  -n epocgs \
  -v 1.0.0 \
  --description "Echo Prime Omega Collectibles Grading System" \
  --url "https://echo-op.com/downloads/epocgs" \
  --maintainer "ECHO PRIME" \
  --license "Proprietary" \
  -C dist/EPOCGS \
  -p installers/epocgs_1.0.0_amd64.deb \
  .
```

**Linux (.rpm):**
```bash
fpm -s dir -t rpm \
  -n epocgs \
  -v 1.0.0 \
  --description "Echo Prime Omega Collectibles Grading System" \
  --url "https://echo-op.com/downloads/epocgs" \
  --maintainer "ECHO PRIME" \
  --license "Proprietary" \
  -C dist/EPOCGS \
  -p installers/epocgs-1.0.0-1.x86_64.rpm \
  .
```

#### Step 4: Create Portable ZIP

```bash
cd dist
zip -r ../installers/EPOCGS-1.0.0-Windows-Portable.zip EPOCGS/
```

---

## 📋 BUILD OUTPUT

After successful build, you'll have:

```
installers/
├── EPOCGS-1.0.0-Windows-Setup.exe      (~150 MB) - Windows installer
├── EPOCGS-1.0.0-Windows-Portable.zip   (~120 MB) - Windows portable
├── EPOCGS-1.0.0-macOS.dmg              (~160 MB) - macOS disk image
├── epocgs_1.0.0_amd64.deb              (~130 MB) - Debian/Ubuntu package
├── epocgs-1.0.0-1.x86_64.rpm           (~130 MB) - Fedora/RHEL package
└── EPOCGS-1.0.0-Linux-Portable.zip     (~120 MB) - Linux portable
```

---

## 🔍 VERIFICATION

### Test the Executable

**Windows:**
```bash
cd dist/EPOCGS
./EPOCGS.exe
```

**macOS:**
```bash
open dist/EPOCGS.app
```

**Linux:**
```bash
cd dist/EPOCGS
./EPOCGS
```

### Test the Installer

**Windows:**
```bash
# Run installer
installers/EPOCGS-1.0.0-Windows-Setup.exe

# Verify installed
dir "C:\Program Files\EPOCGS"

# Test launch
"C:\Program Files\EPOCGS\EPOCGS.exe"
```

**macOS:**
```bash
# Mount DMG
open installers/EPOCGS-1.0.0-macOS.dmg

# Drag to Applications
# Test launch
open /Applications/EPOCGS.app
```

**Linux (Debian/Ubuntu):**
```bash
# Install .deb
sudo dpkg -i installers/epocgs_1.0.0_amd64.deb

# Fix dependencies if needed
sudo apt --fix-broken install

# Test launch
epocgs
```

**Linux (Fedora/RHEL):**
```bash
# Install .rpm
sudo rpm -i installers/epocgs-1.0.0-1.x86_64.rpm

# Test launch
epocgs
```

---

## 📤 DISTRIBUTION

### Upload to Website

**Destination:** `P:/SOVEREIGN_APPS/website/public/downloads/epocgs/`

```bash
# Copy installers
cp installers/* P:/SOVEREIGN_APPS/website/public/downloads/epocgs/

# Update manifest.json
cd P:/SOVEREIGN_APPS/website/public/downloads/epocgs/
cat > manifest.json << EOF
{
  "app_name": "EPOCGS",
  "version": "1.0.0",
  "release_date": "2026-01-06",
  "platforms": {
    "windows": {
      "installer": "EPOCGS-1.0.0-Windows-Setup.exe",
      "portable": "EPOCGS-1.0.0-Windows-Portable.zip",
      "size_mb": 150
    },
    "macos": {
      "dmg": "EPOCGS-1.0.0-macOS.dmg",
      "size_mb": 160
    },
    "linux": {
      "deb": "epocgs_1.0.0_amd64.deb",
      "rpm": "epocgs-1.0.0-1.x86_64.rpm",
      "portable": "EPOCGS-1.0.0-Linux-Portable.zip",
      "size_mb": 130
    }
  },
  "changelog": [
    "Initial release",
    "AI-powered grading with Claude, Gemini, GPT-4",
    "Support for 8 item types",
    "Firebase cloud sync",
    "Price research integration",
    "Marketplace listing creation"
  ]
}
EOF
```

### Website Download Page

Update `P:/SOVEREIGN_APPS/website/app/downloads/epocgs/page.tsx` metadata:

```typescript
export const metadata = {
  title: 'Download EPOCGS - Desktop App',
  description: 'Download the EPOCGS Collectibles Grading System for Windows, macOS, and Linux. AI-powered grading with cloud sync.',
};

const downloads = {
  windows: {
    installer: '/downloads/epocgs/EPOCGS-1.0.0-Windows-Setup.exe',
    portable: '/downloads/epocgs/EPOCGS-1.0.0-Windows-Portable.zip',
    size: '150 MB',
  },
  macos: {
    dmg: '/downloads/epocgs/EPOCGS-1.0.0-macOS.dmg',
    size: '160 MB',
  },
  linux: {
    deb: '/downloads/epocgs/epocgs_1.0.0_amd64.deb',
    rpm: '/downloads/epocgs/epocgs-1.0.0-1.x86_64.rpm',
    portable: '/downloads/epocgs/EPOCGS-1.0.0-Linux-Portable.zip',
    size: '130 MB',
  },
};
```

---

## 🔐 CODE SIGNING (Optional but Recommended)

### Windows Code Signing

**Get a Code Signing Certificate:**
- DigiCert
- Sectigo
- GlobalSign

**Sign the executable:**
```bash
signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com /td sha256 /fd sha256 installers/EPOCGS-1.0.0-Windows-Setup.exe
```

### macOS Code Signing

**Get an Apple Developer Certificate:**
- Enroll in Apple Developer Program
- Create Developer ID certificate

**Sign the app:**
```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application: ECHO PRIME" dist/EPOCGS.app
```

**Notarize for Gatekeeper:**
```bash
# Create ZIP
ditto -c -k --keepParent dist/EPOCGS.app EPOCGS.zip

# Submit for notarization
xcrun notarytool submit EPOCGS.zip --apple-id you@example.com --password app-specific-password --team-id TEAM_ID

# Staple notarization ticket
xcrun stapler staple dist/EPOCGS.app
```

### Linux (AppImage Signing)

```bash
gpg --detach-sign --armor installers/EPOCGS-1.0.0-Linux-Portable.zip
```

---

## 🐛 TROUBLESHOOTING

### PyInstaller Issues

**Missing modules:**
```bash
# Add to hidden imports in epocgs.spec
hiddenimports = [
    'your_missing_module',
]
```

**Large file size:**
```bash
# Exclude unnecessary packages
excludes = [
    'matplotlib',
    'scipy',
    'pandas',
]
```

**Runtime errors:**
```bash
# Enable debug mode
pyinstaller --debug=all epocgs.spec
```

### Windows Installer Issues

**NSIS errors:**
- Check paths in installer.nsi
- Verify dist/EPOCGS/ exists
- Run with /V4 flag for verbose output

### macOS Issues

**Code signing required:**
- macOS 10.15+ requires notarization
- Use `--no-sign` for testing only

**DMG creation fails:**
- Check icon paths
- Ensure .app bundle exists
- Try with `--no-internet-enable`

### Linux Issues

**Missing dependencies:**
```bash
# Debian/Ubuntu
ldd dist/EPOCGS/EPOCGS
sudo apt install missing-packages

# Fedora/RHEL
ldd dist/EPOCGS/EPOCGS
sudo dnf install missing-packages
```

**Permission denied:**
```bash
chmod +x dist/EPOCGS/EPOCGS
```

---

## 📊 SIZE OPTIMIZATION

### Reduce Executable Size

**1. Exclude dev dependencies:**
```bash
pip install --no-dev -r requirements.txt
```

**2. Use UPX compression:**
```bash
# Install UPX
# Windows: choco install upx
# macOS: brew install upx
# Linux: apt install upx-ucl

# Enable in epocgs.spec
upx=True
upx_exclude=[]
```

**3. Strip debug symbols:**
```bash
strip=True  # In epocgs.spec
```

**Expected sizes after optimization:**
- Windows: ~100 MB (from 150 MB)
- macOS: ~110 MB (from 160 MB)
- Linux: ~90 MB (from 130 MB)

---

## 🔄 UPDATE PROCESS

### Version Bump

**Update in 3 places:**
1. `setup.py` - version="1.0.1"
2. `scripts/build_installers.py` - APP_VERSION = "1.0.1"
3. `epocgs.spec` - (if hardcoded anywhere)

### Build New Release

```bash
# Bump version
git tag v1.0.1

# Build new installers
python scripts/build_installers.py

# Upload to website
cp installers/* P:/SOVEREIGN_APPS/website/public/downloads/epocgs/

# Update manifest.json

# Deploy website
cd P:/SOVEREIGN_APPS/website
vercel --prod --yes
```

---

## 📝 CHECKLIST

### Pre-Build
- [ ] All tests passing
- [ ] Version bumped
- [ ] Changelog updated
- [ ] README.md current
- [ ] License file present
- [ ] Icon files exist (icon.ico, icon.icns)

### Build
- [ ] Clean build directories
- [ ] PyInstaller build succeeds
- [ ] Windows installer created
- [ ] macOS DMG created
- [ ] Linux packages created
- [ ] Portable ZIPs created

### Testing
- [ ] Test Windows installer
- [ ] Test macOS DMG
- [ ] Test Linux .deb
- [ ] Test Linux .rpm
- [ ] Test portable versions
- [ ] Verify app launches
- [ ] Verify AI grading works
- [ ] Verify Firebase sync
- [ ] Verify price research

### Distribution
- [ ] Upload to website
- [ ] Update download page
- [ ] Update manifest.json
- [ ] Deploy website
- [ ] Announce release
- [ ] Monitor downloads

---

*EPOCGS Desktop App Build & Distribution Guide*
*ECHO OMEGA PRIME | Authority 11.0*

