#!/bin/bash
# Build script for MoneyTracker macOS packaging

set -e

echo "💰 MoneyTracker macOS Build Script"
echo "=================================="

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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install -r ../requirements.txt
pip install pyinstaller

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf build/ dist/ __pycache__/ *.spec.bak MoneyTracker-mac/ *.dmg

# Build with PyInstaller
print_status "Building macOS app with PyInstaller..."
pyinstaller ../packaging/MoneyTracker.spec --clean --noconfirm

# Check if build was successful
if [ -d "dist/MoneyTracker.app" ]; then
    print_success "PyInstaller build completed successfully!"
    print_status "App bundle created: dist/MoneyTracker.app"
    
    # Create DMG for distribution
    print_status "Creating DMG for distribution..."
    mkdir -p MoneyTracker-mac
    cp -r dist/MoneyTracker.app MoneyTracker-mac/
    
    # Create a nice DMG with background and layout
    print_status "Packaging DMG..."
    if command -v hdiutil >/dev/null 2>&1; then
        hdiutil create -volname "MoneyTracker" -srcfolder MoneyTracker-mac -ov -format UDZO MoneyTracker-mac.dmg
        print_success "DMG created: MoneyTracker-mac.dmg"
    else
        print_warning "hdiutil not available, copying app bundle instead"
        cp -r dist/MoneyTracker.app ./
    fi
    
    echo ""
    print_status "Build information:"
    ls -lah dist/MoneyTracker.app
    if [ -f "MoneyTracker-mac.dmg" ]; then
        ls -lah MoneyTracker-mac.dmg
    fi
    echo ""
    
    print_success "✅ Build complete! You can now:"
    echo "  • Run directly: open dist/MoneyTracker.app"
    if [ -f "MoneyTracker-mac.dmg" ]; then
        echo "  • Distribute: MoneyTracker-mac.dmg"
    fi
    echo "  • Install: drag MoneyTracker.app to Applications folder"
    
else
    print_error "PyInstaller build failed!"
    exit 1
fi

# Deactivate virtual environment
deactivate

echo ""
print_success "🎉 macOS build process completed!"