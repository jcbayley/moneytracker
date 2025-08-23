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
        
        # First, get all recurring transactions that need processing
        with Database.get_db() as db:
            recurring = db.execute('''
                SELECT * FROM recurring_transactions 
                WHERE is_active = 1 AND (end_date IS NULL OR end_date >= ?)
            ''', (today,)).fetchall()
        
        # Process each recurring transaction separately to avoid database locks
        for r in recurring:
            last_processed = datetime.strptime(r['last_processed'], '%Y-%m-%d').date()
            current_amount = r['amount']
            try:
                increment_amount = r['increment_amount'] or 0
            except (KeyError, IndexError):
                increment_amount = 0
            
            # Process all missed occurrences up to today
            next_date = RecurringModel._calculate_next_date(last_processed, r['frequency'])
            original_last_processed = last_processed
            
            while next_date <= today:
                # Apply increment before creating transaction
                current_amount += increment_amount
                
                # Handle transfers differently from regular transactions
                if r['type'] == 'transfer' and r['payee']:
                    # For transfers, payee contains the destination account name
                    # Find the destination account ID by name
                    with Database.get_db() as db:
                        dest_account = db.execute(
                            'SELECT id FROM accounts WHERE name = ?', (r['payee'],)
                        ).fetchone()
                    
                    if dest_account:
                        # Create transfer (both debit and credit transactions)
                        TransactionModel.create_transfer(
                            r['account_id'], dest_account['id'], 
                            abs(current_amount), next_date,
                            r['payee'], r['category'], r['notes'], r['project'], r['id']
                        )
                    else:
                        # Fallback: create single transaction if dest account not found
                        print(f"Warning: Destination account '{r['payee']}' not found for recurring transfer")
                        TransactionModel.create(
                            r['account_id'], -abs(current_amount), next_date, r['type'],
                            r['payee'], r['category'], r['notes'], r['project'], r['id']
                        )
                else:
                    # Regular transaction (income/expense)
                    amount = current_amount
                    if r['type'] == 'expense':
                        amount = -abs(current_amount)
                    else:
                        amount = abs(current_amount)
                        
                    TransactionModel.create(
                        r['account_id'], amount, next_date, r['type'],
                        r['payee'], r['category'], r['notes'], r['project'], r['id']
                    )
                
                processed += 1
                
                # Update for next iteration
                last_processed = next_date
                next_date = RecurringModel._calculate_next_date(next_date, r['frequency'])
            
            # Update the database only if this recurring transaction had occurrences
            if last_processed != original_last_processed:
                with Database.get_db() as db:
                    db.execute(
                        'UPDATE recurring_transactions SET last_processed = ?, amount = ? WHERE id = ?',
                        (last_processed, current_amount, r['id'])
                    )
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