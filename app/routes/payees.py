"""Payee routes."""
from flask import Blueprint, request, jsonify
from ..models.payee import PayeeModel

payees_bp = Blueprint('payees', __name__)


@payees_bp.route('/api/payees', methods=['GET', 'POST'])
def payees():
    """Handle payee operations."""
    if request.method == 'POST':
        data = request.json
        success = PayeeModel.create(data['name'])
        
        if success:
            return jsonify({'message': 'Payee created'})
        else:
            return jsonify({'message': 'Payee already exists'})
    
    payees = PayeeModel.get_all()
    return jsonify([dict(row) for row in payees])