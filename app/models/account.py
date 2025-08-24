"""Account operations and queries."""
from ..database import Database


def get_all():
    """Get all accounts ordered by type and name."""
    with Database.get_db() as db:
        return db.execute('SELECT * FROM accounts ORDER BY type, name').fetchall()


def create(name, account_type, balance=0):
    """Create a new account."""
    with Database.get_db() as db:
        cursor = db.execute(
            'INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)',
            (name, account_type, balance)
        )
        db.commit()
        return cursor.lastrowid


def update(account_id, name, account_type):
    """Update an existing account."""
    with Database.get_db() as db:
        db.execute(
            'UPDATE accounts SET name = ?, type = ? WHERE id = ?',
            (name, account_type, account_id)
        )
        db.commit()


def update_balance(account_id, amount, db=None):
    """Update account balance by adding amount."""
    if db:
        # Use existing connection
        db.execute(
            'UPDATE accounts SET balance = balance + ? WHERE id = ?',
            (amount, account_id)
        )
    else:
        # Create new connection (for standalone use)
        with Database.get_db() as db:
            db.execute(
                'UPDATE accounts SET balance = balance + ? WHERE id = ?',
                (amount, account_id)
            )
            db.commit()


def get_by_id(account_id):
    """Get account by ID."""
    with Database.get_db() as db:
        return db.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()


def get_total_balance(account_types=None):
    """Get total balance across accounts, optionally filtered by types."""
    with Database.get_db() as db:
        if account_types:
            placeholders = ",".join(["?" for _ in account_types])
            query = f'SELECT SUM(balance) FROM accounts WHERE type IN ({placeholders})'
            result = db.execute(query, account_types).fetchone()[0]
        else:
            result = db.execute('SELECT SUM(balance) FROM accounts').fetchone()[0]
        return result or 0