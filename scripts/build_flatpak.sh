#!/bin/bash
# Flatpak build script for Money Tracker

set -e

echo "📦 MoneyTracker Flatpak Builder"
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

# Check if flatpak-builder is installed
if ! command -v flatpak-builder &> /dev/null; then
    print_error "flatpak-builder is not installed"
    echo "Please install it with:"
    echo "  sudo dnf install flatpak-builder  # Fedora"
    echo "  sudo apt install flatpak-builder  # Ubuntu/Debian"
    echo "  sudo pacman -S flatpak-builder    # Arch"
    exit 1
fi

# Check if PyInstaller build exists
if [ ! -f "scripts/dist/MoneyTracker" ]; then
    print_error "PyInstaller build not found! Run ./build.sh first"
    exit 1
fi

# Create build directory
BUILD_DIR="flatpak-build"
print_status "Creating build directory: $BUILD_DIR"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build Flatpak
print_status "Building Flatpak package..."
SCRIPT_DIR="$(pwd)"
# Get the actual directory where this script is located
SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_REAL_DIR="$(dirname "$SCRIPT_PATH")"
PROJECT_ROOT="$(dirname "$SCRIPT_REAL_DIR")"
print_status "Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"
flatpak-builder --force-clean --install "scripts/$BUILD_DIR" packaging/com.moneytracker.MoneyTracker.yml
cd "$SCRIPT_DIR"

if [ $? -eq 0 ]; then
    print_success "✅ Flatpak build completed successfully!"
    print_status "Flatpak has been installed locally"
    echo ""
    print_success "🎉 You can now:"
    echo "  • Run: flatpak run com.moneytracker.MoneyTracker"
    echo "  • Export: flatpak build-export repo $BUILD_DIR"
    echo "  • Create bundle: flatpak build-bundle repo MoneyTracker.flatpak com.moneytracker.MoneyTracker"
else
    print_error "Flatpak build failed!"
    exit 1
fi

print_success "🚀 Flatpak build process completed!"