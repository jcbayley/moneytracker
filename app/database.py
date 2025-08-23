"""Database connection and initialization module."""
import sqlite3
from contextlib import contextmanager
from flask import current_app


class Database:
    """Database connection and query management."""
    
    @staticmethod
    def get_connection():
        """Get database connection with row factory."""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        return db
    
    @staticmethod
    @contextmanager
    def get_db():
        """Context manager for database connections."""
        db = Database.get_connection()
        try:
            yield db
        finally:
            db.close()
    
    @staticmethod
    def init_db():
        """Initialize the database with tables."""
        with Database.get_db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    balance REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    date DATE NOT NULL,
                    type TEXT NOT NULL,
                    payee TEXT,
                    category TEXT,
                    notes TEXT,
                    recurring_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                );
                
                CREATE TABLE IF NOT EXISTS recurring_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    payee TEXT,
                    category TEXT,
                    notes TEXT,
                    frequency TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE,
                    last_processed DATE,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                );
                
                CREATE TABLE IF NOT EXISTS payees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_account INTEGER DEFAULT 0,
                    account_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                );
                
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            db.commit()