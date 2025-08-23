"""Backup management routes."""
from flask import Blueprint, jsonify, request, current_app, send_file
from app.utils.backup import BackupManager
import os


backup_bp = Blueprint('backup', __name__, url_prefix='/api/backup')


def get_backup_manager():
    """Get backup manager instance with current app settings."""
    settings = getattr(current_app, '_backup_settings', {})
    return BackupManager(
        db_path=current_app.config['DATABASE'],
        backup_dir=settings.get('directory', 'backups'),
        settings=settings
    )


@backup_bp.route('/status', methods=['GET'])
def get_backup_status():
    """Get current backup status and list of backups."""
    try:
        backup_manager = get_backup_manager()
        status = backup_manager.get_backup_status()
        backups = backup_manager.list_backups()
        
        return jsonify({
            'status': status,
            'backups': backups
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/create', methods=['POST'])
def create_backup():
    """Create a new backup manually."""
    try:
        data = request.get_json() or {}
        custom_name = data.get('name')
        
        backup_manager = get_backup_manager()
        backup_path = backup_manager.create_backup(custom_name)
        
        return jsonify({
            'success': True,
            'backup_path': backup_path,
            'message': 'Backup created successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/restore', methods=['POST'])
def restore_backup():
    """Restore database from a backup."""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': 'Backup filename is required'}), 400
        
        backup_manager = get_backup_manager()
        backup_manager.restore_backup(data['filename'])
        
        return jsonify({
            'success': True,
            'message': f'Database restored from {data["filename"]}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/download/<filename>', methods=['GET'])
def download_backup(filename):
    """Download a backup file."""
    try:
        backup_manager = get_backup_manager()
        backup_path = backup_manager.backup_dir / filename
        
        if not backup_path.exists():
            return jsonify({'error': 'Backup file not found'}), 404
        
        return send_file(
            str(backup_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/settings', methods=['GET', 'POST'])
def backup_settings():
    """Get or update backup settings."""
    if request.method == 'GET':
        backup_manager = get_backup_manager()
        return jsonify(backup_manager.settings)
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No settings provided'}), 400
        
        # Update backup settings in app context
        if not hasattr(current_app, '_backup_settings'):
            current_app._backup_settings = {}
        
        current_app._backup_settings.update(data)
        
        # Restart backup manager with new settings if needed
        backup_manager = get_backup_manager()
        if 'enabled' in data:
            if data['enabled']:
                backup_manager.start_periodic_backup()
            else:
                backup_manager.stop_periodic_backup()
        
        return jsonify({
            'success': True,
            'message': 'Backup settings updated',
            'settings': backup_manager.settings
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500