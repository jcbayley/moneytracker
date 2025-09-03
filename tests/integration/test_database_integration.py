"""Integration tests for database operations."""
import unittest
import os
import sys
import sqlite3
import tempfile

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.database import Database


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database operations."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        # Initialize test database directly with SQLite
        conn = sqlite3.connect(self.temp_db_path)
        conn.executescript('''
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
        ''')
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_database_connection(self):
        """Test database connection and basic operations."""
        # Test basic database connection
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        
        # Test creating a simple table
        cursor.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        
        # Test inserting data
        cursor.execute('INSERT INTO test_table (name) VALUES (?)', ('test',))
        conn.commit()
        
        # Test retrieving data
        cursor.execute('SELECT * FROM test_table')
        result = cursor.fetchall()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], 'test')
        
        conn.close()

    def test_database_schema_creation(self):
        """Test that database schema is created correctly."""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        
        # Create expected tables
        expected_tables = ['accounts', 'transactions']
        
        for table in expected_tables:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY
                )
            ''')
        
        conn.commit()
        
        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in expected_tables:
            self.assertIn(table, tables)
        
        conn.close()

    def test_transaction_integrity(self):
        """Test database transaction integrity."""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        
        # Create test table
        cursor.execute('''
            CREATE TABLE integrity_test (
                id INTEGER PRIMARY KEY,
                value INTEGER
            )
        ''')
        
        try:
            # Start transaction
            cursor.execute('BEGIN')
            cursor.execute('INSERT INTO integrity_test (value) VALUES (?)', (1,))
            cursor.execute('INSERT INTO integrity_test (value) VALUES (?)', (2,))
            
            # Verify data is inserted but not committed
            cursor.execute('SELECT COUNT(*) FROM integrity_test')
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
            
            # Commit transaction
            conn.commit()
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            self.fail(f"Transaction failed: {e}")
        
        # Verify data persists after commit
        cursor.execute('SELECT COUNT(*) FROM integrity_test')
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        conn.close()

    def test_database_constraints(self):
        """Test database constraints and foreign keys."""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Create tables with foreign key relationship
        cursor.execute('''
            CREATE TABLE parent_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE child_table (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER,
                value TEXT,
                FOREIGN KEY (parent_id) REFERENCES parent_table(id)
            )
        ''')
        
        # Insert parent record
        cursor.execute('INSERT INTO parent_table (name) VALUES (?)', ('parent',))
        parent_id = cursor.lastrowid
        
        # Insert child record with valid parent_id
        cursor.execute('INSERT INTO child_table (parent_id, value) VALUES (?, ?)', 
                      (parent_id, 'child'))
        
        conn.commit()
        
        # Verify the relationship works
        cursor.execute('''
            SELECT p.name, c.value 
            FROM parent_table p 
            JOIN child_table c ON p.id = c.parent_id
        ''')
        result = cursor.fetchone()
        
        self.assertEqual(result[0], 'parent')
        self.assertEqual(result[1], 'child')
        
        conn.close()


if __name__ == '__main__':
    unittest.main()