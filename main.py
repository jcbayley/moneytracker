"""
Refactored Money Tracker Flask Application
Main application file using modular structure
"""
from flask import Flask, render_template
import os
import json
import argparse
import threading
import time
import webbrowser

from app.database import Database
from app.routes.accounts import accounts_bp
from app.routes.transactions import transactions_bp
from app.routes.recurring import recurring_bp
from app.routes.payees import payees_bp
from app.routes.categories import categories_bp
from app.routes.analytics import analytics_bp
from app.routes.data import data_bp
from app.routes.settings import settings_bp
from app.routes.backup import backup_bp
from app.utils.backup import BackupManager


def load_settings():
    """Load settings from settings.json file."""
    settings_file = 'settings.json'
    default_settings = {
        'database_path': 'money_tracker.db',
        'backup': {
            'enabled': True,
            'interval_hours': 24,
            'max_backups': 7,
            'directory': 'backups'
        }
    }
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                return {**default_settings, **settings}
        except:
            print("Warning: Could not load settings.json, using defaults")
            return default_settings
    else:
        # Create default settings file
        with open(settings_file, 'w') as f:
            json.dump(default_settings, f, indent=4)
        return default_settings

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    settings = load_settings()
    app.config['DATABASE'] = settings['database_path']
    
    # Store backup settings in app context
    app._backup_settings = settings.get('backup', {})
    
    # Register blueprints
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(payees_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(backup_bp)
    
    @app.route('/')
    def index():
        """Serve the main HTML page"""
        return render_template('app.html')
    
    return app


def start_backup_system(app):
    """Initialize and start the backup system."""
    with app.app_context():
        backup_settings = getattr(app, '_backup_settings', {})
        if backup_settings.get('enabled', True):
            # Determine backup directory - should be relative to database location
            db_path = app.config['DATABASE']
            db_dir = os.path.dirname(os.path.abspath(db_path))
            backup_dir = os.path.join(db_dir, backup_settings.get('directory', 'backups'))
            
            backup_manager = BackupManager(
                db_path=db_path,
                backup_dir=backup_dir,
                settings=backup_settings
            )
            backup_manager.start_periodic_backup()
            
            # Store backup manager in app context for later access
            app._backup_manager = backup_manager


def run_desktop_app(app):
    """Run the app in a desktop window using PyQt5"""
    try:
        # Try PyQt5 first (most reliable for bundling)
        from PyQt5.QtWidgets import QApplication, QMainWindow
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtCore import QUrl, QTimer
        from PyQt5.QtGui import QIcon
        import sys
        
        # Create QApplication
        qt_app = QApplication(sys.argv if sys.argv else ['MoneyTracker'])
        
        # Create main window
        window = QMainWindow()
        window.setWindowTitle('💰 Money Tracker')
        window.resize(1400, 900)
        window.setMinimumSize(800, 600)
        
        # Create web engine view
        webview = QWebEngineView()
        window.setCentralWidget(webview)
        
        def start_flask():
            app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False, threaded=True)
        
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        
        def load_app():
            webview.load(QUrl('http://127.0.0.1:5000'))
        
        # Wait for Flask to start, then load the app
        QTimer.singleShot(2000, load_app)  # 2 second delay
        
        # Show window and start Qt event loop
        window.show()
        print("🖥️  Opening Money Tracker native window...")
        
        # Handle window close event
        def on_window_close():
            print("💾 Shutting down Money Tracker...")
            
            # Run backup before shutdown
            try:
                if hasattr(app, '_backup_manager'):
                    print("🔄 Creating backup before shutdown...")
                    backup_manager = getattr(app, '_backup_manager')
                    backup_file = backup_manager.create_backup()
                    if backup_file:
                        print(f"✅ Backup created: {backup_file}")
                    else:
                        print("⚠️  Backup failed")
                else:
                    print("⚠️  No backup manager available")
            except Exception as e:
                print(f"⚠️  Backup error: {e}")
            
            qt_app.quit()
        
        window.closeEvent = lambda event: on_window_close()
        
        try:
            qt_app.exec_()
        finally:
            print("🔄 Server shutdown complete")
            sys.exit(0)
        
    except ImportError as e:
        print(f"❌ PyQt5 not available: {e}")
        print("🔄 Trying pywebview fallback...")
        try_webview_fallback(app)
    except Exception as e:
        print(f"❌ Error: Could not start Qt window: {e}")
        print("🔄 Trying pywebview fallback...")
        try_webview_fallback(app)


def try_webview_fallback(app):
    """Fallback to pywebview if PyQt5 fails"""
    try:
        import webview
        
        def start_flask():
            app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
        
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        time.sleep(2)
        
        def on_webview_close():
            """Handle webview window close"""
            try:
                if hasattr(app, '_backup_manager'):
                    print("🔄 Creating backup before shutdown...")
                    backup_manager = getattr(app, '_backup_manager')
                    backup_file = backup_manager.create_backup()
                    if backup_file:
                        print(f"✅ Backup created: {backup_file}")
            except Exception as e:
                print(f"⚠️  Backup error: {e}")
        
        webview.create_window(
            title='💰 Money Tracker',
            url='http://127.0.0.1:5000',
            width=1400,
            height=900,
            min_size=(800, 600),
            resizable=True,
            on_top=False
        )
        
        try:
            webview.start(debug=False)
        finally:
            on_webview_close()
        
    except Exception as e:
        print(f"❌ Webview also failed: {e}")
        print("🔄 Falling back to browser mode...")
        run_browser_app(app)


def run_browser_app(app, host='0.0.0.0', port=5000):
    """Run the app and open in default browser"""
    import socket
    import signal
    
    # Set up backup on shutdown for browser mode
    def backup_and_exit(signum, frame):
        print("\n💾 Shutting down Money Tracker...")
        try:
            if hasattr(app, '_backup_manager'):
                print("🔄 Creating backup before shutdown...")
                backup_manager = getattr(app, '_backup_manager')
                backup_file = backup_manager.create_backup()
                if backup_file:
                    print(f"✅ Backup created: {backup_file}")
        except Exception as e:
            print(f"⚠️  Backup error: {e}")
        finally:
            print("🔄 Server shutdown complete")
            os._exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, backup_and_exit)
    signal.signal(signal.SIGTERM, backup_and_exit)
    
    # Find an available port if the default is in use
    def find_free_port(start_port):
        for p in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', p))
                    return p
            except OSError:
                continue
        return None
    
    # Check if port is available
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
    except OSError:
        print(f"⚠️  Port {port} is in use, finding available port...")
        port = find_free_port(5000)
        if port is None:
            print("❌ No available ports found")
            return
        print(f"✅ Using port {port}")
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{port}')
        print(f"🌐 Money Tracker opened in browser at http://localhost:{port}")
    
    # Start browser opener in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    try:
        # Run Flask app
        app.run(debug=False, host=host, port=port)
    except KeyboardInterrupt:
        backup_and_exit(None, None)


def run_headless(app, host='0.0.0.0', port=5000):
    """Run the app in headless mode (no GUI)"""
    print("\n" + "="*50)
    print("💰 Money Tracker - Headless Mode")
    print("="*50)
    print(f"\n✅ Server running at: http://localhost:{port}")
    print(f"🔗 API available at: http://localhost:{port}/api/")
    print("\n📋 Available endpoints:")
    print("  • GET  /api/accounts")
    print("  • POST /api/accounts")
    print("  • GET  /api/transactions")
    print("  • POST /api/transactions")
    print("  • GET  /api/recurring")
    print("  • GET  /api/analytics/stats")
    print("  • GET  /api/analytics/charts")
    print("  • GET  /api/export")
    print("\n💡 Access the web interface from any browser")
    print("🛑 Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    app.run(debug=False, host=host, port=port)


def print_startup_info():
    """Print startup information"""
    print("\n" + "="*50)
    print("💰 Money Tracker Flask Server (Refactored)")
    print("="*50)
    print("\n📊 Features:")
    print("  • Modular architecture")
    print("  • Real SQLite database (money_tracker.db)")
    print("  • Recurring transactions")
    print("  • Multiple account support")
    print("  • Analytics and charts")
    print("  • Data export functionality")
    print("  • Automatic database backups")
    print("\n💡 Tips:")
    print("  • Data persists between sessions")
    print("  • Access from any device on your network")
    print("  • Database file: money_tracker.db")
    print("  • Backups stored in: backups/ directory")


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Money Tracker - Personal Finance Manager')
    parser.add_argument('--mode', choices=['window', 'browser', 'headless'], 
                       default='window',
                       help='Run mode: window (desktop app), browser (opens browser), headless (no GUI)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to run the server on (default: 5000)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    
    args = parser.parse_args()
    
    # Create the Flask app
    app = create_app()
    
    # Initialize database on first run
    if not os.path.exists(app.config['DATABASE']):
        print("Creating new database...")
        with app.app_context():
            Database.init_db()
        print("Database initialized (empty)")
    else:
        print(f"Using existing database: {app.config['DATABASE']}")
        # Run migrations for existing database
        with app.app_context():
            Database.migrate_add_project_column()
    
    # Start backup system
    start_backup_system(app)
    
    # Run based on selected mode
    if args.mode == 'window':
        print_startup_info()
        print("\n🖥️  Starting in Desktop Window mode...")
        print("="*50 + "\n")
        run_desktop_app(app)
        
    elif args.mode == 'browser':
        print_startup_info()
        print(f"\n🌐 Starting in Browser mode on http://localhost:{args.port}")
        print("🚀 Opening browser automatically...")
        print("="*50 + "\n")
        run_browser_app(app, args.host, args.port)
        
    elif args.mode == 'headless':
        run_headless(app, args.host, args.port)
    
    else:
        print("❌ Invalid mode specified")
        parser.print_help()