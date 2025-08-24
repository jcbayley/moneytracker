"""AI Query routes for natural language transaction analysis."""
from flask import Blueprint, request, jsonify
import json
import os
import threading
from datetime import datetime, timedelta
from ..models import ai_query

ai_query_bp = Blueprint('ai_query', __name__)

# Global variable to track download progress
download_progress = {'progress': 0, 'status': 'idle', 'message': ''}

@ai_query_bp.route('/api/ai/query', methods=['POST'])
def process_ai_query():
    """Process natural language query about transactions."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400
            
        user_query = data['query'].strip()
        if not user_query:
            return jsonify({'error': 'Empty query'}), 400
            
        # Process the query with AI
        ai_service = ai_query.AIQueryService()
        result = ai_service.process_query(user_query)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'AI query failed: {str(e)}'}), 500


@ai_query_bp.route('/api/ai/model/status', methods=['GET'])
def get_model_status():
    """Check if the AI model is downloaded and ready."""
    try:
        ai_service = ai_query.AIQueryService()
        status = ai_service.check_model_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': f'Failed to check model status: {str(e)}'}), 500


@ai_query_bp.route('/api/ai/model/download', methods=['POST'])
def download_model():
    """Start downloading the AI model."""
    global download_progress
    
    try:
        # Check if already downloading
        if download_progress['status'] == 'downloading':
            return jsonify({'message': 'Download already in progress'}), 200
        
        # Reset progress
        download_progress = {'progress': 0, 'status': 'downloading', 'message': 'Starting download...'}
        
        # Start download in background thread
        ai_service = ai_query.AIQueryService()
        thread = threading.Thread(target=ai_service.download_model, args=(download_progress,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'Model download started'}), 200
        
    except Exception as e:
        download_progress['status'] = 'error'
        download_progress['message'] = str(e)
        return jsonify({'error': f'Failed to start download: {str(e)}'}), 500


@ai_query_bp.route('/api/ai/model/download/progress', methods=['GET'])
def get_download_progress():
    """Get the current download progress."""
    global download_progress
    return jsonify(download_progress)


