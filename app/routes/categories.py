"""Category routes."""
from flask import Blueprint, request, jsonify
from ..models import category

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/api/categories', methods=['GET', 'POST'])  
def categories():
    """Handle category operations."""
    if request.method == 'POST':
        data = request.json
        success = category.create(data['name'])
        
        if success:
            return jsonify({'message': 'Category created'})
        else:
            return jsonify({'message': 'Category already exists'})
    
    categories = category.get_all()
    return jsonify(categories)