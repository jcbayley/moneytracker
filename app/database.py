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
    def migrate_add_project_column():
        """Add project column to existing tables if it doesn't exist."""
        with Database.get_db() as db:
            # Check if project column exists in transactions table
            cursor = db.execute("PRAGMA table_info(transactions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'project' not in columns:
                db.execute('ALTER TABLE transactions ADD COLUMN project TEXT')
                print("Added project column to transactions table")
            
            # Check if project column exists in recurring_transactions table
            cursor = db.execute("PRAGMA table_info(recurring_transactions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'project' not in columns:
                db.execute('ALTER TABLE recurring_transactions ADD COLUMN project TEXT')
                print("Added project column to recurring_transactions table")
            
            db.commit()
    
    @staticmethod
    def migrate_add_increment_column():
        """Add increment_amount column to recurring_transactions if it doesn't exist."""
        with Database.get_db() as db:
            cursor = db.execute("PRAGMA table_info(recurring_transactions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'increment_amount' not in columns:
                db.execute('ALTER TABLE recurring_transactions ADD COLUMN increment_amount REAL DEFAULT 0')
                print("Added increment_amount column to recurring_transactions table")
                db.commit()
    
    @staticmethod
    def migrate_add_projects_table():
        """Create projects table if it doesn't exist."""
        with Database.get_db() as db:
            # Check if projects table exists
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
            if not cursor.fetchone():
                db.execute('''
                    CREATE TABLE projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("Created projects table")
                db.commit()
    
    @staticmethod
    def migrate_add_project_category_notes():
        """Add category and notes columns to projects table if they don't exist."""
        with Database.get_db() as db:
            # Check current columns in projects table
            cursor = db.execute("PRAGMA table_info(projects)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'category' not in columns:
                db.execute('ALTER TABLE projects ADD COLUMN category TEXT')
                print("Added category column to projects table")
            
            if 'notes' not in columns:
                db.execute('ALTER TABLE projects ADD COLUMN notes TEXT')
                print("Added notes column to projects table")
            
            db.commit()
    
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
                    project TEXT,
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
                    project TEXT,
                    frequency TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE,
                    last_processed DATE,
                    increment_amount REAL DEFAULT 0,
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
                
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            db.commit()