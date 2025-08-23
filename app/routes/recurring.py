"""Recurring transaction routes."""
from flask import Blueprint, jsonify
from ..models.recurring import RecurringModel

recurring_bp = Blueprint('recurring', __name__)


@recurring_bp.route('/api/recurring', methods=['GET'])
def get_recurring():
    """Get all recurring transactions."""
    recurring = RecurringModel.get_all_active()
    return jsonify([dict(row) for row in recurring])


@recurring_bp.route('/api/recurring/<int:recurring_id>', methods=['DELETE'])
def delete_recurring(recurring_id):
    """Delete (deactivate) a recurring transaction."""
    RecurringModel.deactivate(recurring_id)
    return jsonify({'message': 'Recurring transaction deleted'})


@recurring_bp.route('/api/recurring/process', methods=['POST'])
def process_recurring():
    """Process due recurring transactions."""
    processed = RecurringModel.process_due()
    
    message = f'Processed {processed} recurring transaction(s)' if processed > 0 else 'No recurring transactions are due'
    return jsonify({'message': message, 'processed': processed})