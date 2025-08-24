"""Analytics queries and calculations."""
from ..database import Database


def get_stats(start_date=None, end_date=None, account_types=None):
        """Get financial statistics with filters."""
        with Database.get_db() as db:
            # Build filters
            date_filter = ''
            account_filter = ''
            params_income = []
            params_expense = []
            
            if start_date and end_date:
                date_filter = ' AND t.date BETWEEN ? AND ?'
                params_income.extend([start_date, end_date])
                params_expense.extend([start_date, end_date])
            elif start_date:
                date_filter = ' AND t.date >= ?'
                params_income.append(start_date)
                params_expense.append(start_date)
            elif end_date:
                date_filter = ' AND t.date <= ?'
                params_income.append(end_date)
                params_expense.append(end_date)
            
            if account_types:
                placeholders = ",".join(["?" for _ in account_types])
                account_filter = f' AND a.type IN ({placeholders})'
                params_income.extend(account_types)
                params_expense.extend(account_types)
            
            # Income query
            income_query = f'''
                SELECT SUM(t.amount) FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'income'{date_filter}{account_filter}
            '''
            
            # Expense query
            expense_query = f'''
                SELECT SUM(t.amount) FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'expense'{date_filter}{account_filter}
            '''
            
            income = db.execute(income_query, params_income).fetchone()[0] or 0
            expenses = abs(db.execute(expense_query, params_expense).fetchone()[0] or 0)
            
            return {
                'monthly_income': income,
                'monthly_expenses': expenses,
                'net_monthly': income - expenses
            }
    
def get_category_spending(start_date=None, end_date=None, account_types=None):
        """Get spending by category."""
        with Database.get_db() as db:
            date_filter = ''
            account_filter = ''
            params = []
            
            if start_date and end_date:
                date_filter = ' AND t.date BETWEEN ? AND ?'
                params.extend([start_date, end_date])
            elif start_date:
                date_filter = ' AND t.date >= ?'
                params.append(start_date)
            elif end_date:
                date_filter = ' AND t.date <= ?'
                params.append(end_date)
            
            if account_types:
                placeholders = ",".join(["?" for _ in account_types])
                account_filter = f' AND a.type IN ({placeholders})'
                params.extend(account_types)
            
            query = f'''
                SELECT t.category, SUM(ABS(t.amount)) as total
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'expense' AND t.category IS NOT NULL{date_filter}{account_filter}
                GROUP BY t.category
                ORDER BY total DESC
            '''
            
            return db.execute(query, params).fetchall()
    
def get_monthly_trend(start_date=None, end_date=None, account_types=None):
        """Get monthly income/expense/savings/investment trend."""
        with Database.get_db() as db:
            date_filter = ''
            account_filter = ''
            params = []
            
            if start_date and end_date:
                date_filter = ' AND t.date BETWEEN ? AND ?'
                params.extend([start_date, end_date])
            elif start_date:
                date_filter = ' AND t.date >= ?'
                params.append(start_date)
            elif end_date:
                date_filter = ' AND t.date <= ?'
                params.append(end_date)
            
            if account_types:
                placeholders = ",".join(["?" for _ in account_types])
                account_filter = f' AND a.type IN ({placeholders})'
                params.extend(account_types)
            
            query = f'''
                SELECT 
                    strftime('%Y-%m', t.date) as month,
                    SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) as income,
                    SUM(CASE WHEN t.type = 'expense' THEN ABS(t.amount) ELSE 0 END) as expenses,
                    SUM(CASE 
                        WHEN t.type = 'transfer' AND t.amount > 0 AND a.type = 'savings' THEN t.amount 
                        ELSE 0 
                    END) as savings,
                    SUM(CASE 
                        WHEN t.type = 'transfer' AND t.amount > 0 AND a.type = 'investment' THEN t.amount 
                        ELSE 0 
                    END) as investments
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE 1=1{date_filter}{account_filter}
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6
            '''
            
            trends = db.execute(query, params).fetchall()
            return list(reversed(trends))
    
def get_category_trends(start_date=None, end_date=None, account_types=None):
        """Get category trends over time."""
        with Database.get_db() as db:
            date_filter = ''
            account_filter = ''
            params = []
            
            if start_date and end_date:
                date_filter = ' AND t.date BETWEEN ? AND ?'
                params.extend([start_date, end_date])
            elif start_date:
                date_filter = ' AND t.date >= ?'
                params.append(start_date)
            elif end_date:
                date_filter = ' AND t.date <= ?'
                params.append(end_date)
            
            if account_types:
                placeholders = ",".join(["?" for _ in account_types])
                account_filter = f' AND a.type IN ({placeholders})'
                params.extend(account_types)
            
            query = f'''
                SELECT 
                    strftime('%Y-%m', t.date) as month,
                    t.category,
                    SUM(ABS(t.amount)) as total
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.type = 'expense' AND t.category IS NOT NULL{date_filter}{account_filter}
                GROUP BY month, t.category
                ORDER BY month DESC, total DESC
            '''
            
            return db.execute(query, params).fetchall()