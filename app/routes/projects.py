"""Project routes."""
from flask import Blueprint, request, jsonify
from ..models import project

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/api/projects', methods=['GET', 'POST'])
def projects():
    """Handle project operations."""
    if request.method == 'POST':
        data = request.json
        
        if not data.get('name'):
            return jsonify({'error': 'Project name is required'}), 400
        
        try:
            project_id = project.create(data['name'], data.get('description'), data.get('category'), data.get('notes'))
            return jsonify({'message': 'Project created', 'id': project_id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    else:  # GET
        projects = project.get_all_with_stats()
        return jsonify([dict(row) for row in projects])


@projects_bp.route('/api/projects/<int:project_id>', methods=['GET', 'PUT', 'DELETE'])
def project_detail(project_id):
    """Handle individual project operations."""
    if request.method == 'GET':
        analytics = project.get_project_analytics(project_id)
        if not analytics:
            return jsonify({'error': 'Project not found'}), 404
        return jsonify(analytics)
    
    elif request.method == 'PUT':
        data = request.json
        
        if not data.get('name'):
            return jsonify({'error': 'Project name is required'}), 400
        
        try:
            project.update(project_id, data['name'], data.get('description'), data.get('category'), data.get('notes'))
            return jsonify({'message': 'Project updated'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            project.delete(project_id)
            return jsonify({'message': 'Project deleted'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400


@projects_bp.route('/api/projects/names', methods=['GET'])
def project_names():
    """Get just project names for dropdown."""
    projects = project.get_all()
    return jsonify([{'id': p['id'], 'name': p['name']} for p in projects])