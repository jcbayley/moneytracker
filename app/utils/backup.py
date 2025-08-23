"""Database backup utility module."""
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import json


class BackupManager:
    """Manages periodic database backups."""
    
    def __init__(self, db_path, backup_dir="backups", settings=None):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Default settings
        self.settings = {
            'enabled': True,
            'interval_hours': 24,
            'max_backups': 7,
            'compress': False
        }
        
        if settings:
            self.settings.update(settings)
        
        self._stop_event = threading.Event()
        self._backup_thread = None
    
    def create_backup(self, custom_name=None):
        """Create a single backup of the database."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if custom_name:
            backup_name = f"{custom_name}_{timestamp}.db"
        else:
            backup_name = f"money_tracker_backup_{timestamp}.db"
        
        backup_path = self.backup_dir / backup_name
        
        # Create backup using SQLite's backup API for consistency
        try:
            # Open source database
            source_db = sqlite3.connect(self.db_path)
            
            # Create backup database
            backup_db = sqlite3.connect(str(backup_path))
            
            # Perform backup
            source_db.backup(backup_db)
            
            # Close connections
            backup_db.close()
            source_db.close()
            
            print(f"✅ Database backup created: {backup_path}")
            
            # Clean up old backups if needed
            self._cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            # Clean up failed backup file
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def _cleanup_old_backups(self):
        """Remove old backups beyond the configured limit."""
        if self.settings['max_backups'] <= 0:
            return
        
        # Get all backup files sorted by creation time (newest first)
        backup_files = []
        for file in self.backup_dir.glob("*.db"):
            if file.name.startswith("money_tracker_backup_"):
                backup_files.append(file)
        
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove excess backups
        if len(backup_files) > self.settings['max_backups']:
            for old_backup in backup_files[self.settings['max_backups']:]:
                try:
                    old_backup.unlink()
                    print(f"🗑️  Removed old backup: {old_backup.name}")
                except Exception as e:
                    print(f"⚠️  Failed to remove old backup {old_backup.name}: {e}")
    
    def list_backups(self):
        """List all available backups with their details."""
        backups = []
        
        for file in self.backup_dir.glob("*.db"):
            if file.name.startswith("money_tracker_backup_"):
                stat = file.stat()
                backups.append({
                    'filename': file.name,
                    'path': str(file),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime),
                    'size_mb': round(stat.st_size / (1024 * 1024), 2)
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups
    
    def restore_backup(self, backup_filename):
        """Restore database from a backup file."""
        backup_path = self.backup_dir / backup_filename
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Create a backup of current database before restore
        current_backup = self.create_backup("pre_restore")
        print(f"📦 Created backup of current database: {current_backup}")
        
        try:
            # Copy backup file to database location
            shutil.copy2(str(backup_path), self.db_path)
            print(f"✅ Database restored from: {backup_filename}")
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            raise
    
    def start_periodic_backup(self):
        """Start the periodic backup thread."""
        if not self.settings['enabled']:
            print("📴 Periodic backups are disabled")
            return
        
        if self._backup_thread and self._backup_thread.is_alive():
            print("⚠️  Backup thread is already running")
            return
        
        self._stop_event.clear()
        self._backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        self._backup_thread.start()
        
        interval_hours = self.settings['interval_hours']
        print(f"🔄 Periodic backups started (every {interval_hours} hours)")
    
    def stop_periodic_backup(self):
        """Stop the periodic backup thread."""
        if self._backup_thread and self._backup_thread.is_alive():
            self._stop_event.set()
            self._backup_thread.join(timeout=5)
            print("⏹️  Periodic backups stopped")
    
    def _backup_loop(self):
        """Main backup loop running in background thread."""
        interval_seconds = self.settings['interval_hours'] * 3600
        
        while not self._stop_event.is_set():
            try:
                # Wait for the specified interval or until stop event
                if self._stop_event.wait(timeout=interval_seconds):
                    break  # Stop event was set
                
                # Create backup
                if os.path.exists(self.db_path):
                    self.create_backup()
                else:
                    print("⚠️  Database file not found, skipping backup")
                    
            except Exception as e:
                print(f"❌ Periodic backup error: {e}")
                # Continue running even if one backup fails
    
    def get_backup_status(self):
        """Get current backup status and statistics."""
        backups = self.list_backups()
        
        status = {
            'enabled': self.settings['enabled'],
            'interval_hours': self.settings['interval_hours'],
            'max_backups': self.settings['max_backups'],
            'backup_directory': str(self.backup_dir),
            'total_backups': len(backups),
            'thread_running': self._backup_thread and self._backup_thread.is_alive(),
            'latest_backup': backups[0] if backups else None,
            'total_backup_size_mb': sum(b['size_mb'] for b in backups)
        }
        
        return status