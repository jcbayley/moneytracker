#!/bin/bash
# Install GUI dependencies for Money Tracker native window support

echo "🔧 Installing GUI dependencies for Money Tracker..."

# Detect Linux distribution
if [ -f /etc/fedora-release ]; then
    echo "📦 Detected Fedora - installing GTK dependencies..."
    sudo dnf install -y python3-gobject gtk3-devel gobject-introspection-devel webkit2gtk3-devel
    
elif [ -f /etc/debian_version ]; then
    echo "📦 Detected Debian/Ubuntu - installing GTK dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0
    
elif [ -f /etc/arch-release ]; then
    echo "📦 Detected Arch Linux - installing GTK dependencies..."
    sudo pacman -S python-gobject gtk3 webkit2gtk
    
else
    echo "❌ Unsupported Linux distribution"
    echo "💡 Please install GTK3 and Python GObject bindings manually"
    echo "   Or install PyQt5: pip install PyQt5"
    exit 1
fi

echo "✅ GUI dependencies installed successfully!"
echo "🚀 You can now run Money Tracker in native window mode"