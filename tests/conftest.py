"""Pytest configuration and shared fixtures."""
import pytest
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    # Create a basic schema for testing
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create basic tables
    cursor.execute('''
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            date TEXT NOT NULL,
            payee TEXT,
            amount REAL NOT NULL,
            category TEXT,
            notes TEXT,
            type TEXT DEFAULT 'expense',
            recurring_id INTEGER,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def sample_account_data():
    """Sample account data for testing."""
    return {
        'name': 'Test Account',
        'type': 'current',
        'balance': 1000.0
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return {
        'account_id': 1,
        'date': '2023-01-01',
        'payee': 'Test Payee',
        'amount': -50.0,
        'category': 'Shopping',
        'notes': 'Test transaction',
        'type': 'expense'
    }


@pytest.fixture
def mock_database():
    """Mock database context manager."""
    from unittest.mock import MagicMock
    
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.__enter__.return_value = mock_cursor
    mock_db.__exit__.return_value = None
    
    return mock_db, mock_cursor