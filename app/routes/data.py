"""Data import/export routes."""
from flask import Blueprint, request, jsonify
from ..utils import import_export

data_bp = Blueprint('data', __name__)


@data_bp.route('/api/database/info')
def database_info():
    """Get database information."""
    return jsonify(import_export.get_database_info())


@data_bp.route('/api/export')
def export_database():
    """Export the database file."""
    return import_export.export_database()


@data_bp.route('/api/import', methods=['POST'])
def import_database():
    """Import a database file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    result, status_code = import_export.import_database(file)
    return jsonify(result), status_code


@data_bp.route('/api/export/csv')
def export_csv():
    """Export transactions to CSV format."""
    return import_export.export_csv()


@data_bp.route('/api/import/csv', methods=['POST'])
def import_csv():
    """Import transactions from CSV format."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    result, status_code = import_export.import_csv(file)
    return jsonify(result), status_code