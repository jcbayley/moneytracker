"""Unit tests for transaction model functions."""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models import transaction


class TestTransactionModel(unittest.TestCase):
    """Test cases for transaction model functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_transactions = [
            {'id': 1, 'date': '2023-01-01', 'payee': 'Test Store', 'amount': -50.0, 
             'category': 'Shopping', 'account_id': 1, 'account_name': 'Checking', 'frequency': None},
            {'id': 2, 'date': '2023-01-02', 'payee': 'Salary', 'amount': 2000.0, 
             'category': 'Income', 'account_id': 1, 'account_name': 'Checking', 'frequency': 'monthly'},
        ]

    @patch('app.models.transaction.Database.get_db')
    def test_get_filtered_no_filters(self, mock_get_db):
        """Test get_filtered with no filters returns all transactions."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = self.sample_transactions
        mock_get_db.return_value.__enter__.return_value = mock_db

        result = transaction.get_filtered()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['payee'], 'Test Store')
        mock_db.execute.assert_called_once()

    @patch('app.models.transaction.Database.get_db')
    def test_get_filtered_with_account_id(self, mock_get_db):
        """Test get_filtered with account_id filter."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [self.sample_transactions[0]]
        mock_get_db.return_value.__enter__.return_value = mock_db

        result = transaction.get_filtered(account_id=1)
        
        self.assertEqual(len(result), 1)
        # Verify that account_id parameter was used in query
        args, kwargs = mock_db.execute.call_args
        self.assertIn('account_id', args[0])
        self.assertIn(1, args[1])

    @patch('app.models.transaction.Database.get_db')
    def test_get_filtered_with_search(self, mock_get_db):
        """Test get_filtered with search term."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [self.sample_transactions[0]]
        mock_get_db.return_value.__enter__.return_value = mock_db

        result = transaction.get_filtered(search="Store")
        
        self.assertEqual(len(result), 1)
        # Verify search parameters were used
        args, kwargs = mock_db.execute.call_args
        self.assertIn('LIKE', args[0])
        # Should have 4 search terms (payee, notes, category, amount)
        search_params = [param for param in args[1] if '%Store%' in str(param)]
        self.assertEqual(len(search_params), 4)

    @patch('app.models.transaction.Database.get_db')
    def test_get_filtered_with_date_range(self, mock_get_db):
        """Test get_filtered with date range."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = self.sample_transactions
        mock_get_db.return_value.__enter__.return_value = mock_db

        result = transaction.get_filtered(date_from='2023-01-01', date_to='2023-01-31')
        
        self.assertEqual(len(result), 2)
        args, kwargs = mock_db.execute.call_args
        self.assertIn('date >=', args[0])
        self.assertIn('date <=', args[0])
        self.assertIn('2023-01-01', args[1])
        self.assertIn('2023-01-31', args[1])

    @patch('app.models.transaction.Database.get_db')
    def test_get_filtered_with_category(self, mock_get_db):
        """Test get_filtered with category filter."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [self.sample_transactions[1]]
        mock_get_db.return_value.__enter__.return_value = mock_db

        result = transaction.get_filtered(category='Income')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['category'], 'Income')
        args, kwargs = mock_db.execute.call_args
        self.assertIn('category', args[0])
        self.assertIn('Income', args[1])

    @patch('app.models.transaction.Database.get_db')
    def test_get_filtered_with_limit(self, mock_get_db):
        """Test get_filtered with custom limit."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [self.sample_transactions[0]]
        mock_get_db.return_value.__enter__.return_value = mock_db

        result = transaction.get_filtered(limit=1)
        
        args, kwargs = mock_db.execute.call_args
        self.assertIn('LIMIT', args[0])
        self.assertEqual(args[1][-1], 1)  # Last parameter should be the limit


if __name__ == '__main__':
    unittest.main()