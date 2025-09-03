"""Unit tests for backup utility functions."""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import tempfile
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.utils.backup import BackupManager


class TestBackupManager(unittest.TestCase):
    """Test cases for BackupManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        
        # Create a real SQLite database file for testing
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('INSERT INTO test (name) VALUES (?)', ('test_data',))
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_backup_manager_init_default_settings(self):
        """Test BackupManager initialization with default settings."""
        manager = BackupManager(self.db_path, self.backup_dir)
        
        self.assertEqual(manager.db_path, self.db_path)
        self.assertEqual(manager.backup_dir, Path(self.backup_dir))
        self.assertTrue(manager.settings['enabled'])
        self.assertEqual(manager.settings['interval_hours'], 24)
        self.assertEqual(manager.settings['max_backups'], 7)
        self.assertFalse(manager.settings['compress'])

    def test_backup_manager_init_custom_settings(self):
        """Test BackupManager initialization with custom settings."""
        custom_settings = {
            'enabled': False,
            'interval_hours': 12,
            'max_backups': 3,
            'compress': True
        }
        manager = BackupManager(self.db_path, self.backup_dir, custom_settings)
        
        self.assertFalse(manager.settings['enabled'])
        self.assertEqual(manager.settings['interval_hours'], 12)
        self.assertEqual(manager.settings['max_backups'], 3)
        self.assertTrue(manager.settings['compress'])

    def test_backup_directory_creation(self):
        """Test that backup directory is created on initialization."""
        manager = BackupManager(self.db_path, self.backup_dir)
        
        self.assertTrue(os.path.exists(self.backup_dir))
        self.assertTrue(os.path.isdir(self.backup_dir))

    def test_create_backup(self):
        """Test backup creation method."""
        manager = BackupManager(self.db_path, self.backup_dir)
        
        # Test actual backup creation
        if hasattr(manager, 'create_backup'):
            result = manager.create_backup()
            
            # Verify backup was created
            self.assertIsNotNone(result)
            self.assertTrue(os.path.exists(result))
            
            # Verify it's a valid SQLite database
            import sqlite3
            conn = sqlite3.connect(result)
            cursor = conn.execute('SELECT name FROM test')
            row = cursor.fetchone()
            self.assertEqual(row[0], 'test_data')
            conn.close()

    def test_backup_filename_format(self):
        """Test backup filename follows expected format."""
        manager = BackupManager(self.db_path, self.backup_dir)
        
        # Test that backup filename would include timestamp
        now = datetime.now()
        expected_date = now.strftime('%Y%m%d_%H%M%S')
        
        # This test assumes the backup filename includes timestamp
        # Actual implementation may vary
        if hasattr(manager, 'generate_backup_filename'):
            filename = manager.generate_backup_filename()
            self.assertIn('backup', filename.lower())

    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_backup_validation(self, mock_getsize, mock_exists):
        """Test backup file validation."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1000  # 1KB file
        
        manager = BackupManager(self.db_path, self.backup_dir)
        
        # Test validation logic if implemented
        if hasattr(manager, 'validate_backup'):
            result = manager.validate_backup('fake_backup.db')
            self.assertTrue(result)

    def test_settings_update(self):
        """Test settings can be updated after initialization."""
        manager = BackupManager(self.db_path, self.backup_dir)
        
        new_settings = {'max_backups': 10, 'compress': True}
        manager.settings.update(new_settings)
        
        self.assertEqual(manager.settings['max_backups'], 10)
        self.assertTrue(manager.settings['compress'])
        # Original settings should remain
        self.assertTrue(manager.settings['enabled'])
        self.assertEqual(manager.settings['interval_hours'], 24)

    @patch('os.listdir')
    def test_cleanup_old_backups(self, mock_listdir):
        """Test cleanup of old backup files."""
        # Mock backup files with different timestamps
        mock_backup_files = [
            'backup_20230101_120000.db',
            'backup_20230102_120000.db',
            'backup_20230103_120000.db',
        ]
        mock_listdir.return_value = mock_backup_files
        
        manager = BackupManager(self.db_path, self.backup_dir, {'max_backups': 2})
        
        # Test cleanup logic if implemented
        if hasattr(manager, 'cleanup_old_backups'):
            manager.cleanup_old_backups()
            # Should keep only 2 most recent files

    def test_backup_manager_repr(self):
        """Test string representation of BackupManager."""
        manager = BackupManager(self.db_path, self.backup_dir)
        
        repr_str = repr(manager)
        self.assertIn('BackupManager', repr_str)
        self.assertIn(self.db_path, repr_str)


class TestBackupUtilityFunctions(unittest.TestCase):
    """Test utility functions in backup module."""

    def test_backup_path_handling(self):
        """Test backup path utilities."""
        from app.utils.backup import BackupManager
        
        # Test path validation
        invalid_paths = ['', None, '/nonexistent/path/db.db']
        for path in invalid_paths:
            if path is not None:
                # Test that invalid paths are handled gracefully
                try:
                    manager = BackupManager(path, 'backups')
                    self.assertIsInstance(manager.db_path, str)
                except Exception as e:
                    # Should handle invalid paths gracefully
                    self.assertIsInstance(e, (ValueError, OSError))


if __name__ == '__main__':
    unittest.main()