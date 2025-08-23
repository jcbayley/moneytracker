"""Settings routes."""
from flask import Blueprint, request, jsonify
import json
import os

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Handle settings operations."""
    settings_file = 'settings.json'
    
    if request.method == 'POST':
        data = request.json
        
        # Load current settings
        current_settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    current_settings = json.load(f)
            except:
                pass
        
        # Update with new data
        current_settings.update(data)
        
        # Save settings
        try:
            with open(settings_file, 'w') as f:
                json.dump(current_settings, f, indent=4)
            return jsonify({'message': 'Settings saved successfully'})
        except Exception as e:
            return jsonify({'error': f'Failed to save settings: {str(e)}'}), 500
    
    # GET request - return current settings
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                settings_data = json.load(f)
                return jsonify(settings_data)
        except:
            pass
    
    # Return defaults if file doesn't exist or can't be read
    return jsonify({'database_path': 'money_tracker.db'})