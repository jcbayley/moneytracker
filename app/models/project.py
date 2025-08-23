"""Project model and operations."""
from ..database import Database


class ProjectModel:
    """Project operations."""
    
    @staticmethod
    def get_all():
        """Get all projects."""
        with Database.get_db() as db:
            return db.execute('''
                SELECT * FROM projects 
                ORDER BY name
            ''').fetchall()
    
    @staticmethod
    def create(name, description=None):
        """Create a new project."""
        with Database.get_db() as db:
            cursor = db.execute(
                'INSERT INTO projects (name, description) VALUES (?, ?)',
                (name, description)
            )
            db.commit()
            return cursor.lastrowid
    
    @staticmethod
    def update(project_id, name, description=None):
        """Update a project."""
        with Database.get_db() as db:
            db.execute(
                'UPDATE projects SET name = ?, description = ? WHERE id = ?',
                (name, description, project_id)
            )
            db.commit()
    
    @staticmethod
    def delete(project_id):
        """Delete a project."""
        with Database.get_db() as db:
            db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            db.commit()
    
    @staticmethod
    def get_project_analytics(project_id):
        """Get analytics for a specific project."""
        with Database.get_db() as db:
            # Get project details
            project = db.execute(
                'SELECT * FROM projects WHERE id = ?', (project_id,)
            ).fetchone()
            
            if not project:
                return None
            
            # Get total spent/earned
            totals = db.execute('''
                SELECT 
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_spent,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_earned,
                    COUNT(*) as transaction_count
                FROM transactions 
                WHERE project = ?
            ''', (project['name'],)).fetchone()
            
            # Get spending by category
            categories = db.execute('''
                SELECT 
                    category,
                    SUM(ABS(amount)) as total,
                    COUNT(*) as count
                FROM transactions 
                WHERE project = ? AND amount < 0
                GROUP BY category
                ORDER BY total DESC
            ''', (project['name'],)).fetchall()
            
            # Get recent transactions
            recent_transactions = db.execute('''
                SELECT t.*, a.name as account_name
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.project = ?
                ORDER BY t.date DESC, t.created_at DESC
                LIMIT 10
            ''', (project['name'],)).fetchall()
            
            return {
                'project': dict(project),
                'totals': dict(totals) if totals else {'total_spent': 0, 'total_earned': 0, 'transaction_count': 0},
                'categories': [dict(cat) for cat in categories],
                'recent_transactions': [dict(t) for t in recent_transactions]
            }
    
    @staticmethod
    def get_all_with_stats():
        """Get all projects with basic statistics."""
        with Database.get_db() as db:
            return db.execute('''
                SELECT 
                    p.*,
                    COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END), 0) as total_spent,
                    COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0) as total_earned,
                    COALESCE(COUNT(t.id), 0) as transaction_count
                FROM projects p
                LEFT JOIN transactions t ON p.name = t.project
                GROUP BY p.id, p.name, p.description, p.created_at
                ORDER BY p.name
            ''').fetchall()