"""Recurring transaction model and operations."""
from datetime import datetime, timedelta
from ..database import Database
from .transaction import TransactionModel


class RecurringModel:
    """Recurring transaction operations."""
    
    @staticmethod
    def get_all_active():
        """Get all active recurring transactions with next dates."""
        with Database.get_db() as db:
            return db.execute('''
                SELECT r.*, a.name as account_name,
                CASE 
                    WHEN r.frequency = 'daily' THEN date(r.last_processed, '+1 day')
                    WHEN r.frequency = 'weekly' THEN date(r.last_processed, '+7 days')
                    WHEN r.frequency = 'biweekly' THEN date(r.last_processed, '+14 days')
                    WHEN r.frequency = 'monthly' THEN date(r.last_processed, '+1 month')
                    WHEN r.frequency = 'quarterly' THEN date(r.last_processed, '+3 months')
                    WHEN r.frequency = 'yearly' THEN date(r.last_processed, '+1 year')
                END as next_date
                FROM recurring_transactions r
                JOIN accounts a ON r.account_id = a.id
                WHERE r.is_active = 1
            ''').fetchall()
    
    @staticmethod
    def create(account_id, amount, trans_type, payee, category, notes, project, 
               frequency, start_date, end_date=None, increment_amount=0):
        """Create a recurring transaction."""
        with Database.get_db() as db:
            cursor = db.execute('''
                INSERT INTO recurring_transactions 
                (account_id, amount, type, payee, category, notes, project, frequency, 
                 start_date, end_date, last_processed, increment_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (account_id, amount, trans_type, payee, category, notes, project,
                  frequency, start_date, end_date, start_date, increment_amount))
            db.commit()
            return cursor.lastrowid
    
    @staticmethod
    def deactivate(recurring_id):
        """Deactivate a recurring transaction."""
        with Database.get_db() as db:
            db.execute(
                'UPDATE recurring_transactions SET is_active = 0 WHERE id = ?', 
                (recurring_id,)
            )
            db.commit()
    
    @staticmethod
    def process_due():
        """Process all due recurring transactions."""
        today = datetime.now().date()
        processed = 0
        
        with Database.get_db() as db:
            recurring = db.execute('''
                SELECT * FROM recurring_transactions 
                WHERE is_active = 1 AND (end_date IS NULL OR end_date >= ?)
            ''', (today,)).fetchall()
            
            for r in recurring:
                next_date = RecurringModel._calculate_next_date(
                    datetime.strptime(r['last_processed'], '%Y-%m-%d').date(),
                    r['frequency']
                )
                
                if next_date <= today:
                    # Calculate the new amount with increment
                    current_amount = r['amount']
                    increment_amount = r.get('increment_amount', 0)
                    new_amount = current_amount + increment_amount
                    
                    # Create transaction with current amount
                    TransactionModel.create(
                        r['account_id'], current_amount, next_date, r['type'],
                        r['payee'], r['category'], r['notes'], r['project'], r['id']
                    )
                    
                    # Update last processed date and increment the amount for next time
                    db.execute(
                        'UPDATE recurring_transactions SET last_processed = ?, amount = ? WHERE id = ?',
                        (next_date, new_amount, r['id'])
                    )
                    processed += 1
            
            db.commit()
        
        return processed
    
    @staticmethod
    def _calculate_next_date(last_date, frequency):
        """Calculate the next date for a recurring transaction."""
        if frequency == 'daily':
            return last_date + timedelta(days=1)
        elif frequency == 'weekly':
            return last_date + timedelta(weeks=1)
        elif frequency == 'biweekly':
            return last_date + timedelta(weeks=2)
        elif frequency == 'monthly':
            if last_date.month == 12:
                return last_date.replace(year=last_date.year + 1, month=1)
            else:
                return last_date.replace(month=last_date.month + 1)
        elif frequency == 'quarterly':
            month = last_date.month + 3
            year = last_date.year
            if month > 12:
                month = month - 12
                year = year + 1
            return last_date.replace(year=year, month=month)
        elif frequency == 'yearly':
            return last_date.replace(year=last_date.year + 1)
        
        return last_date