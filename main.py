"""
Refactored Money Tracker Flask Application
Main application file using modular structure
"""
from flask import Flask, render_template
import os
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


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config['DATABASE'] = 'money_tracker.db'
    
    # Register blueprints
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(payees_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(data_bp)
    
    @app.route('/')
    def index():
        """Serve the main HTML page"""
        return render_template('app.html')
    
    return app


def run_desktop_app(app):
    """Run the app in a desktop window using webview"""
    try:
        import webview
        
        def start_flask():
            app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
        
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        
        # Wait for Flask to start
        time.sleep(2)
        
        # Create and start the webview window
        webview.create_window(
            title='💰 Money Tracker',
            url='http://127.0.0.1:5000',
            width=1400,
            height=900,
            min_size=(800, 600),
            resizable=True
        )
        webview.start(debug=False)
        
    except ImportError:
        print("❌ Error: webview package not installed")
        print("📦 Install it with: pip install pywebview")
        print("🔄 Falling back to browser mode...")
        run_browser_app(app)


def run_browser_app(app, host='0.0.0.0', port=5000):
    """Run the app and open in default browser"""
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{port}')
    
    # Start browser opener in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run Flask app
    app.run(debug=False, host=host, port=port)


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
    print("\n💡 Tips:")
    print("  • Data persists between sessions")
    print("  • Access from any device on your network")
    print("  • Database file: money_tracker.db")


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