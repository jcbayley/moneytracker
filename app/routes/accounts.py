"""Account routes."""
from flask import Blueprint, request, jsonify
from ..models.account import AccountModel

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/api/accounts', methods=['GET', 'POST'])
def accounts():
    """Handle account operations."""
    if request.method == 'POST':
        data = request.json
        account_id = AccountModel.create(
            data['name'], 
            data['type'], 
            data.get('balance', 0)
        )
        return jsonify({'id': account_id, 'message': 'Account created'})
    
    accounts = AccountModel.get_all()
    return jsonify([dict(row) for row in accounts])


@accounts_bp.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """Update an account."""
    data = request.json
    AccountModel.update(account_id, data['name'], data['type'])
    return jsonify({'message': 'Account updated'})