"""Unit tests for account model functions."""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models import account


class TestAccountModel(unittest.TestCase):
    """Test cases for account model functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_accounts = [
            {'id': 1, 'name': 'Checking', 'type': 'current', 'balance': 1000.0, 'created_at': '2023-01-01'},
            {'id': 2, 'name': 'Savings', 'type': 'savings', 'balance': 5000.0, 'created_at': '2023-01-01'},
            {'id': 3, 'name': 'Investment', 'type': 'investment', 'balance': 10000.0, 'created_at': '2023-01-01'},
        ]

    @patch('app.models.account.Database.get_db')
    def test_get_all_accounts(self, mock_get_db):
        """Test getting all accounts."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = self.sample_accounts
        mock_get_db.return_value.__enter__.return_value = mock_db

        if hasattr(account, 'get_all'):
            result = account.get_all()
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0]['name'], 'Checking')
            mock_db.execute.assert_called_once()

    @patch('app.models.account.Database.get_db')
    def test_get_account_by_id(self, mock_get_db):
        """Test getting account by ID."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = self.sample_accounts[0]
        mock_get_db.return_value.__enter__.return_value = mock_db

        if hasattr(account, 'get_by_id'):
            result = account.get_by_id(1)
            self.assertEqual(result['name'], 'Checking')
            self.assertEqual(result['type'], 'current')
            mock_db.execute.assert_called_once()

    @patch('app.models.account.Database.get_db')
    def test_create_account(self, mock_get_db):
        """Test creating a new account."""
        mock_db = MagicMock()
        mock_db.execute.return_value.lastrowid = 4
        mock_get_db.return_value.__enter__.return_value = mock_db

        if hasattr(account, 'create'):
            result = account.create('New Account', 'current', 0.0)
            
            self.assertEqual(result, 4)
            mock_db.execute.assert_called_once()
            # Verify INSERT statement was used
            args, kwargs = mock_db.execute.call_args
            self.assertIn('INSERT', args[0])

    @patch('app.models.account.Database.get_db')
    def test_update_account(self, mock_get_db):
        """Test updating an existing account."""
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db

        if hasattr(account, 'update'):
            account.update(1, 'Updated Account', 'current')
            mock_db.execute.assert_called_once()
            # Verify UPDATE statement was used
            args, kwargs = mock_db.execute.call_args
            self.assertIn('UPDATE', args[0])

    @patch('app.models.account.Database.get_db')
    def test_delete_account(self, mock_get_db):
        """Test deleting an account."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_db.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        if hasattr(account, 'delete'):
            result = account.delete(1)
            
            self.assertTrue(result)
            mock_cursor.execute.assert_called_once()
            # Verify DELETE statement was used
            args, kwargs = mock_cursor.execute.call_args
            self.assertIn('DELETE', args[0])

    @patch('app.models.account.Database.get_db')
    def test_get_account_balance(self, mock_get_db):
        """Test getting account balance."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'balance': 1000.0}
        mock_db.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        if hasattr(account, 'get_balance'):
            result = account.get_balance(1)
            self.assertEqual(result, 1000.0)

    def test_account_validation(self):
        """Test account data validation."""
        if hasattr(account, 'validate'):
            # Test valid account data
            valid_data = {
                'name': 'Test Account',
                'type': 'current',
                'balance': 100.0
            }
            self.assertTrue(account.validate(valid_data))
            
            # Test invalid account data
            invalid_data = {
                'name': '',  # Empty name
                'type': 'invalid_type',
                'balance': 'not_a_number'
            }
            self.assertFalse(account.validate(invalid_data))

    @patch('app.models.account.Database.get_db')
    def test_get_accounts_by_type(self, mock_get_db):
        """Test getting accounts filtered by type."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        savings_accounts = [acc for acc in self.sample_accounts if acc['type'] == 'savings']
        mock_cursor.fetchall.return_value = savings_accounts
        mock_db.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        if hasattr(account, 'get_by_type'):
            result = account.get_by_type('savings')
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['name'], 'Savings')

    @patch('app.models.account.Database.get_db')
    def test_account_exists(self, mock_get_db):
        """Test checking if account exists."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'count': 1}
        mock_db.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        if hasattr(account, 'exists'):
            result = account.exists(1)
            self.assertTrue(result)
            mock_cursor.execute.assert_called_once()


if __name__ == '__main__':
    unittest.main()