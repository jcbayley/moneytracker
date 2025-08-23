"""Payee model and operations."""
import sqlite3
from ..database import Database


class PayeeModel:
    """Payee operations and queries."""
    
    @staticmethod
    def get_all():
        """Get all payees including account-based payees."""
        with Database.get_db() as db:
            return db.execute('''
                SELECT p.name, p.is_account, p.account_id
                FROM payees p
                UNION
                SELECT a.name, 1 as is_account, a.id as account_id
                FROM accounts a
                ORDER BY name
            ''').fetchall()
    
    @staticmethod
    def create(name):
        """Create a new payee."""
        with Database.get_db() as db:
            try:
                db.execute('INSERT INTO payees (name) VALUES (?)', (name,))
                db.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Payee already exists
    
    @staticmethod
    def bulk_create(payees):
        """Create multiple payees, ignoring duplicates."""
        with Database.get_db() as db:
            for payee in payees:
                try:
                    db.execute('INSERT OR IGNORE INTO payees (name) VALUES (?)', (payee,))
                except:
                    pass
            db.commit()