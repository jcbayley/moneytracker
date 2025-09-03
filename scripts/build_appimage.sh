#!/bin/bash
# AppImage build script for MoneyTracker

set -e

echo "📦 MoneyTracker AppImage Builder"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if PyInstaller build exists
if [ ! -f "dist/MoneyTracker" ]; then
    print_error "PyInstaller build not found! Run ./build.sh first"
    exit 1
fi

# Create AppDir structure
print_status "Creating AppDir structure..."
rm -rf MoneyTracker.AppDir
mkdir -p MoneyTracker.AppDir/usr/bin
mkdir -p MoneyTracker.AppDir/usr/share/applications
mkdir -p MoneyTracker.AppDir/usr/share/icons/hicolor/256x256/apps

# Copy executable and settings
print_status "Copying executable and configuration..."
cp dist/MoneyTracker MoneyTracker.AppDir/usr/bin/
cp ../settings.json MoneyTracker.AppDir/usr/bin/ 2>/dev/null || echo "Warning: settings.json not found, using defaults"

# Copy desktop file
cp ../packaging/com.moneytracker.MoneyTracker.desktop MoneyTracker.AppDir/
cp ../packaging/com.moneytracker.MoneyTracker.desktop MoneyTracker.AppDir/usr/share/applications/

# Copy application icon
print_status "Copying application icon..."
if [ -f "../packaging/MoneyTracker.png" ]; then
    cp ../packaging/MoneyTracker.png MoneyTracker.AppDir/
    cp ../packaging/MoneyTracker.png MoneyTracker.AppDir/com.moneytracker.MoneyTracker.png
    cp ../packaging/MoneyTracker.png MoneyTracker.AppDir/usr/share/icons/hicolor/256x256/apps/
else
    print_warning "MoneyTracker.png not found, creating placeholder"
fi

# Create AppRun script
print_status "Creating AppRun script..."
cat > MoneyTracker.AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"

# Create writable data directory in user's home
DATA_DIR="${HOME}/.local/share/MoneyTracker"
mkdir -p "${DATA_DIR}"

# Copy default settings if they don't exist
if [ ! -f "${DATA_DIR}/settings.json" ] && [ -f "${HERE}/usr/bin/settings.json" ]; then
    cp "${HERE}/usr/bin/settings.json" "${DATA_DIR}/"
fi

# Change to data directory so app can write files
cd "${DATA_DIR}"

# Execute the app
exec "${HERE}/usr/bin/MoneyTracker" "$@"
EOF

chmod +x MoneyTracker.AppDir/AppRun

# Download appimagetool if not exists
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    print_status "Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x appimagetool-x86_64.AppImage
fi

# Create AppImage
print_status "Building AppImage..."
# Try running appimagetool normally first, then with --appimage-extract-and-run if FUSE fails
if ! ARCH=x86_64 ./appimagetool-x86_64.AppImage MoneyTracker.AppDir MoneyTracker-x86_64.AppImage 2>/dev/null; then
    print_status "FUSE not available, using --appimage-extract-and-run..."
    ARCH=x86_64 ./appimagetool-x86_64.AppImage --appimage-extract-and-run MoneyTracker.AppDir MoneyTracker-x86_64.AppImage
fi

if [ -f "MoneyTracker-x86_64.AppImage" ]; then
    print_success "✅ AppImage created successfully!"
    echo ""
    print_status "AppImage information:"
    ls -lh MoneyTracker-x86_64.AppImage
    echo ""
    print_success "🎉 You can now:"
    echo "  • Run: ./MoneyTracker-x86_64.AppImage"
    echo "  • Distribute: MoneyTracker-x86_64.AppImage"
    echo "  • Install: chmod +x MoneyTracker-x86_64.AppImage && ./MoneyTracker-x86_64.AppImage"
else
    print_error "AppImage build failed!"
    exit 1
fi

# Cleanup
print_status "Cleaning up..."
rm -rf MoneyTracker.AppDir

print_success "🚀 AppImage build completed!"