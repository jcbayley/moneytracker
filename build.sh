#!/bin/bash
# Build script for MoneyTracker cross-platform packaging

set -e

echo "💰 MoneyTracker Build Script"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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
pip install -r requirements.txt

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf build/ dist/ __pycache__/ *.spec.bak

# Build with PyInstaller
print_status "Building executable with PyInstaller..."
pyinstaller MoneyTracker.spec --clean --noconfirm

# Check if build was successful
if [ -f "dist/MoneyTracker" ]; then
    print_success "PyInstaller build completed successfully!"
    print_status "Executable created: dist/MoneyTracker"
    
    # Make executable
    chmod +x dist/MoneyTracker
    
    # Show file info
    echo ""
    print_status "Build information:"
    ls -lh dist/MoneyTracker
    echo ""
    
    print_success "✅ Build complete! You can now:"
    echo "  • Run directly: ./dist/MoneyTracker"
    echo "  • Create AppImage: ./build_appimage.sh"
    echo "  • Build Flatpak: flatpak-builder build-dir com.moneytracker.MoneyTracker.yml"
    
else
    print_error "PyInstaller build failed!"
    exit 1
fi

# Deactivate virtual environment
deactivate

echo ""
print_success "🎉 Build process completed!"