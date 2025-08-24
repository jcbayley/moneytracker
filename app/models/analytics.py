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
                        WHEN a.type = 'savings' AND t.type = 'transfer' THEN t.amount 
                        ELSE 0 
                    END) as savings,
                    SUM(CASE 
                        WHEN a.type = 'investment' AND t.type = 'transfer' THEN t.amount 
                        ELSE 0 
                    END) as investments
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE 1=1{date_filter}{account_filter}
                GROUP BY month
                ORDER BY month DESC
                LIMIT 12
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

def get_top_payees(start_date=None, end_date=None, account_types=None, limit=10):
    """Get top payees by spending amount."""
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
        
        params.append(limit)
        
        query = f'''
            SELECT 
                COALESCE(t.payee, 'Unknown') as payee,
                SUM(ABS(t.amount)) as total
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE t.type = 'expense' 
            AND t.payee IS NOT NULL 
            AND t.payee != ''{date_filter}{account_filter}
            GROUP BY t.payee
            ORDER BY total DESC
            LIMIT ?
        '''
        
        return db.execute(query, params).fetchall()

def get_savings_investments_flow(start_date=None, end_date=None, account_types=None):
    """Get monthly savings and investments flow data."""
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
                SUM(CASE 
                    WHEN a.type = 'savings' AND t.type = 'transfer'
                    THEN t.amount ELSE 0 
                END) as savings_net,
                SUM(CASE 
                    WHEN a.type = 'investment' AND t.type = 'transfer'
                    THEN t.amount ELSE 0 
                END) as investments_net,
                SUM(CASE 
                    WHEN t.type = 'expense'
                    THEN ABS(t.amount) ELSE 0 
                END) as other_outgoing,
                SUM(CASE 
                    WHEN t.type = 'income' 
                    THEN t.amount ELSE 0 
                END) as income
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE 1=1{date_filter}{account_filter}
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        '''
        
        results = db.execute(query, params).fetchall()
        return list(reversed(results))

def get_net_worth_history():
    """Get net worth history over all time (ignoring date ranges)."""
    with Database.get_db() as db:
        query = '''
            WITH 
            all_months AS (
                SELECT DISTINCT strftime('%Y-%m', date) as month
                FROM transactions
                ORDER BY month
            ),
            all_accounts AS (
                SELECT id as account_id FROM accounts
            ),
            month_account_combinations AS (
                SELECT m.month, a.account_id
                FROM all_months m
                CROSS JOIN all_accounts a
            ),
            monthly_transactions AS (
                SELECT 
                    strftime('%Y-%m', t.date) as month,
                    t.account_id,
                    SUM(t.amount) as month_total
                FROM transactions t
                GROUP BY strftime('%Y-%m', t.date), t.account_id
            ),
            monthly_balances AS (
                SELECT 
                    mac.month,
                    mac.account_id,
                    COALESCE(mt.month_total, 0) as month_total
                FROM month_account_combinations mac
                LEFT JOIN monthly_transactions mt ON mac.month = mt.month AND mac.account_id = mt.account_id
            ),
            running_balances AS (
                SELECT 
                    month,
                    account_id,
                    SUM(month_total) OVER (
                        PARTITION BY account_id 
                        ORDER BY month 
                        ROWS UNBOUNDED PRECEDING
                    ) as running_balance
                FROM monthly_balances
            ),
            monthly_net_worth AS (
                SELECT 
                    month,
                    SUM(running_balance) as net_worth
                FROM running_balances
                GROUP BY month
            )
            SELECT month, net_worth
            FROM monthly_net_worth
            ORDER BY month
        '''
        
        return db.execute(query).fetchall()