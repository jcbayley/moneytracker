"""Category operations and queries."""
import sqlite3
from ..database import Database


def get_all():
    """Get all categories ordered by name."""
    with Database.get_db() as db:
        return [row['name'] for row in db.execute(
            'SELECT name FROM categories ORDER BY name'
        ).fetchall()]


def create(name):
    """Create a new category."""
    with Database.get_db() as db:
        try:
            db.execute('INSERT INTO categories (name) VALUES (?)', (name,))
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Category already exists


def bulk_create(categories):
    """Create multiple categories, ignoring duplicates."""
    with Database.get_db() as db:
        for category in categories:
            try:
                db.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
            except:
                pass
        db.commit()