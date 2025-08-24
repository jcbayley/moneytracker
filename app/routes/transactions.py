"""Transaction routes."""
from flask import Blueprint, request, jsonify
from ..models import transaction
from ..models import recurring

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/api/transactions', methods=['GET', 'POST'])
def transactions():
    """Handle transaction operations."""
    if request.method == 'POST':
        try:
            data = request.json
            
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            # Validate required fields
            required_fields = ['account_id', 'amount', 'date', 'type']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            
            # Handle recurring transaction creation
            recurring_id = None
            if data.get('is_recurring'):
                recurring_id = recurring.create(
                    data['account_id'], data['amount'], data['type'],
                    data.get('payee'), data.get('category'), data.get('notes'),
                    data.get('project'), data['frequency'], data['date'], data.get('end_date'),
                    data.get('increment_amount', 0)
                )
            
            # Handle transfer
            if data.get('type') == 'transfer' and data.get('transfer_account_id'):
                transaction.create_transfer(
                    data['account_id'], data['transfer_account_id'], 
                    abs(data['amount']), data['date'],
                    data.get('payee'), data.get('category'), data.get('notes'),
                    data.get('project'), recurring_id
                )
            else:
                # Regular transaction
                amount = data['amount']
                if data['type'] == 'expense':
                    amount = -abs(amount)
                else:
                    amount = abs(amount)
                    
                transaction.create(
                    data['account_id'], amount, data['date'], data['type'],
                    data.get('payee'), data.get('category'), data.get('notes'),
                    data.get('project'), recurring_id
                )
            
            return jsonify({'message': 'Transaction added'})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    try:
        # GET request with filters
        transactions = transaction.get_filtered(
            account_id=request.args.get('account_id'),
            category=request.args.get('category'),
            trans_type=request.args.get('type'),
            date_from=request.args.get('date_from'),
            date_to=request.args.get('date_to'),
            limit=int(request.args.get('limit', 100))
        )
        
        return jsonify([dict(row) for row in transactions])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transactions_bp.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update a transaction."""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['account_id', 'amount', 'date', 'type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        success = transaction.update(
            transaction_id, data['account_id'], data['amount'], 
            data['date'], data['type'], data.get('payee'),
            data.get('category'), data.get('notes'), data.get('project'),
            data.get('transfer_account_id')
        )
        
        if success:
            return jsonify({'message': 'Transaction updated'})
        else:
            return jsonify({'error': 'Transaction not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transactions_bp.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Delete a transaction."""
    try:
        success = transaction.delete(transaction_id)
        
        if success:
            return jsonify({'message': 'Transaction deleted'})
        else:
            return jsonify({'error': 'Transaction not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500