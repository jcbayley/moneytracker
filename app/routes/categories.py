"""Category routes."""
from flask import Blueprint, request, jsonify
from ..models.category import CategoryModel

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/api/categories', methods=['GET', 'POST'])  
def categories():
    """Handle category operations."""
    if request.method == 'POST':
        data = request.json
        success = CategoryModel.create(data['name'])
        
        if success:
            return jsonify({'message': 'Category created'})
        else:
            return jsonify({'message': 'Category already exists'})
    
    categories = CategoryModel.get_all()
    return jsonify(categories)