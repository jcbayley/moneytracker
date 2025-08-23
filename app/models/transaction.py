"""Transaction model and operations."""
from datetime import datetime, timedelta
from ..database import Database
from .account import AccountModel


class TransactionModel:
    """Transaction operations and queries."""
    
    @staticmethod
    def get_filtered(account_id=None, category=None, trans_type=None, date_from=None, limit=100):
        """Get transactions with filters."""
        with Database.get_db() as db:
            query = '''
                SELECT t.*, a.name as account_name, r.frequency
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN recurring_transactions r ON t.recurring_id = r.id
                WHERE 1=1
            '''
            params = []
            
            if account_id:
                query += ' AND t.account_id = ?'
                params.append(account_id)
            
            if category:
                query += ' AND t.category = ?'
                params.append(category)
            
            if trans_type:
                query += ' AND t.type = ?'
                params.append(trans_type)
            
            if date_from:
                query += ' AND t.date >= ?'
                params.append(date_from)
            
            query += ' ORDER BY t.date DESC, t.id DESC LIMIT ?'
            params.append(limit)
            
            return db.execute(query, params).fetchall()
    
    @staticmethod
    def create(account_id, amount, date, trans_type, payee=None, category=None, 
               notes=None, recurring_id=None):
        """Create a single transaction."""
        with Database.get_db() as db:
            cursor = db.execute('''
                INSERT INTO transactions 
                (account_id, amount, date, type, payee, category, notes, recurring_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (account_id, amount, date, trans_type, payee, category, notes, recurring_id))
            
            # Update account balance
            AccountModel.update_balance(account_id, amount)
            db.commit()
            return cursor.lastrowid
    
    @staticmethod
    def create_transfer(from_account_id, to_account_id, amount, date, payee=None, 
                       category=None, notes=None, recurring_id=None):
        """Create a transfer between accounts (dual transactions)."""
        with Database.get_db() as db:
            # Get account names for payees
            from_account = AccountModel.get_by_id(from_account_id)
            to_account = AccountModel.get_by_id(to_account_id)
            
            # From account (negative)
            db.execute('''
                INSERT INTO transactions 
                (account_id, amount, date, type, payee, category, notes, recurring_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (from_account_id, -abs(amount), date, 'transfer',
                  to_account['name'] if to_account else 'Transfer', 
                  category, notes, recurring_id))
            
            # To account (positive)
            db.execute('''
                INSERT INTO transactions 
                (account_id, amount, date, type, payee, category, notes, recurring_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (to_account_id, abs(amount), date, 'transfer',
                  from_account['name'] if from_account else 'Transfer',
                  category, notes, recurring_id))
            
            # Update both account balances
            AccountModel.update_balance(from_account_id, -abs(amount))
            AccountModel.update_balance(to_account_id, abs(amount))
            db.commit()
    
    @staticmethod
    def update(transaction_id, account_id, amount, date, trans_type, payee=None,
               category=None, notes=None, transfer_account_id=None):
        """Update an existing transaction."""
        with Database.get_db() as db:
            # Get current transaction
            current = db.execute(
                'SELECT account_id, amount, type FROM transactions WHERE id = ?', 
                (transaction_id,)
            ).fetchone()
            
            if not current:
                return False
            
            old_amount = current['amount']
            old_account_id = current['account_id']
            
            # Handle transfer logic
            if trans_type == 'transfer' and transfer_account_id:
                dest_account = AccountModel.get_by_id(transfer_account_id)
                if old_amount < 0:  # This was the source transaction
                    new_amount = -abs(amount)
                    payee = dest_account['name'] if dest_account else 'Transfer'
                else:  # This was the destination transaction
                    new_amount = abs(amount)
                    source_account = AccountModel.get_by_id(account_id)
                    payee = source_account['name'] if source_account else 'Transfer'
            else:
                # Regular transaction
                new_amount = -abs(amount) if trans_type == 'expense' else abs(amount)
            
            # Update transaction
            db.execute('''
                UPDATE transactions 
                SET account_id = ?, amount = ?, date = ?, type = ?, payee = ?, category = ?, notes = ?
                WHERE id = ?
            ''', (account_id, new_amount, date, trans_type, payee, category, notes, transaction_id))
            
            # Adjust account balances
            if old_account_id == account_id:
                balance_diff = new_amount - old_amount
                AccountModel.update_balance(old_account_id, balance_diff)
            else:
                AccountModel.update_balance(old_account_id, -old_amount)
                AccountModel.update_balance(account_id, new_amount)
            
            db.commit()
            return True
    
    @staticmethod
    def delete(transaction_id):
        """Delete a transaction."""
        with Database.get_db() as db:
            trans = db.execute(
                'SELECT account_id, amount FROM transactions WHERE id = ?', 
                (transaction_id,)
            ).fetchone()
            
            if trans:
                db.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
                AccountModel.update_balance(trans['account_id'], -trans['amount'])
                db.commit()
                return True
            return False
    
    @staticmethod
    def get_by_category(category, start_date=None, end_date=None, account_types=None):
        """Get transactions for a specific category with filters."""
        with Database.get_db() as db:
            query = '''
                SELECT t.*, a.name as account_name
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.category = ?
            '''
            params = [category]
            
            if start_date and end_date:
                query += ' AND t.date BETWEEN ? AND ?'
                params.extend([start_date, end_date])
            elif start_date:
                query += ' AND t.date >= ?'
                params.append(start_date)
            elif end_date:
                query += ' AND t.date <= ?'
                params.append(end_date)
            
            if account_types:
                placeholders = ",".join(["?" for _ in account_types])
                query += f' AND a.type IN ({placeholders})'
                params.extend(account_types)
            
            query += ' ORDER BY t.date DESC, t.id DESC'
            return db.execute(query, params).fetchall()