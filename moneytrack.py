# money_tracker.py - Complete Flask Money Tracker Application
# Save this file and run with: python money_tracker.py

from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from datetime import datetime, timedelta
import json
import os
import io
import csv
import argparse
import threading
import time
import sys
import webbrowser

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['DATABASE'] = 'money_tracker.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize the database with tables"""
    db = get_db()
    db.executescript('''
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
            recurring_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        );
        
        CREATE TABLE IF NOT EXISTS recurring_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            payee TEXT,
            category TEXT,
            notes TEXT,
            frequency TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            last_processed DATE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        );
        
        CREATE TABLE IF NOT EXISTS payees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_account INTEGER DEFAULT 0,
            account_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        );
        
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    db.commit()
    db.close()

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('app.html')

@app.route('/api/accounts', methods=['GET', 'POST'])
def accounts():
    """Handle account operations"""
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        cursor = db.execute(
            'INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)',
            (data['name'], data['type'], data.get('balance', 0))
        )
        db.commit()
        return jsonify({'id': cursor.lastrowid, 'message': 'Account created'})
    
    accounts = db.execute('SELECT * FROM accounts ORDER BY type, name').fetchall()
    db.close()
    return jsonify([dict(row) for row in accounts])

@app.route('/api/accounts/<int:id>', methods=['PUT'])
def update_account(id):
    """Update an account"""
    db = get_db()
    data = request.json
    
    db.execute(
        'UPDATE accounts SET name = ?, type = ? WHERE id = ?',
        (data['name'], data['type'], id)
    )
    db.commit()
    db.close()
    
    return jsonify({'message': 'Account updated'})

@app.route('/api/payees', methods=['GET', 'POST'])
def payees():
    """Handle payee operations"""
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        try:
            db.execute('INSERT INTO payees (name) VALUES (?)', (data['name'],))
            db.commit()
            return jsonify({'message': 'Payee created'})
        except sqlite3.IntegrityError:
            return jsonify({'message': 'Payee already exists'})
    
    # Get all payees including account-based payees
    payees = db.execute('''
        SELECT p.name, p.is_account, p.account_id
        FROM payees p
        UNION
        SELECT a.name, 1 as is_account, a.id as account_id
        FROM accounts a
        ORDER BY name
    ''').fetchall()
    
    db.close()
    return jsonify([dict(row) for row in payees])

@app.route('/api/categories', methods=['GET', 'POST'])  
def categories():
    """Handle category operations"""
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        try:
            db.execute('INSERT INTO categories (name) VALUES (?)', (data['name'],))
            db.commit()
            return jsonify({'message': 'Category created'})
        except sqlite3.IntegrityError:
            return jsonify({'message': 'Category already exists'})
    
    categories = db.execute('SELECT name FROM categories ORDER BY name').fetchall()
    db.close()
    return jsonify([row['name'] for row in categories])

@app.route('/api/transactions', methods=['GET', 'POST'])
def transactions():
    """Handle transaction operations"""
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        
        # Handle recurring transaction
        if data.get('is_recurring'):
            cursor = db.execute('''
                INSERT INTO recurring_transactions 
                (account_id, amount, type, payee, category, notes, frequency, start_date, end_date, last_processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['account_id'], data['amount'], data['type'],
                data.get('payee'), data.get('category'), data.get('notes'),
                data['frequency'], data['date'], data.get('end_date'), data['date']
            ))
            recurring_id = cursor.lastrowid
        else:
            recurring_id = None
        
        # Handle transfer - create dual transactions
        if data.get('type') == 'transfer' and data.get('transfer_account_id'):
            transfer_account_id = data['transfer_account_id']
            amount = abs(data['amount'])  # Always positive for transfers
            
            # From account (negative)
            db.execute('''
                INSERT INTO transactions 
                (account_id, amount, date, type, payee, category, notes, recurring_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['account_id'], -amount, data['date'], 'transfer',
                data.get('payee'), data.get('category'), data.get('notes'), recurring_id
            ))
            
            # To account (positive) - get destination account name for payee
            dest_account = db.execute('SELECT name FROM accounts WHERE id = ?', (data['account_id'],)).fetchone()
            source_payee = dest_account['name'] if dest_account else 'Transfer'
            
            db.execute('''
                INSERT INTO transactions 
                (account_id, amount, date, type, payee, category, notes, recurring_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transfer_account_id, amount, data['date'], 'transfer',
                source_payee, data.get('category'), data.get('notes'), recurring_id
            ))
            
            # Update both account balances
            db.execute(
                'UPDATE accounts SET balance = balance - ? WHERE id = ?',
                (amount, data['account_id'])
            )
            db.execute(
                'UPDATE accounts SET balance = balance + ? WHERE id = ?',
                (amount, transfer_account_id)
            )
        else:
            # Regular transaction
            db.execute('''
                INSERT INTO transactions 
                (account_id, amount, date, type, payee, category, notes, recurring_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['account_id'], data['amount'], data['date'], data['type'],
                data.get('payee'), data.get('category'), data.get('notes'), recurring_id
            ))
            
            # Update account balance
            db.execute(
                'UPDATE accounts SET balance = balance + ? WHERE id = ?',
                (data['amount'], data['account_id'])
            )
        
        db.commit()
        return jsonify({'message': 'Transaction added'})
    
    # GET request with filters
    account_id = request.args.get('account_id')
    category = request.args.get('category')
    trans_type = request.args.get('type')
    date_from = request.args.get('date_from')
    
    query = '''
        SELECT t.*, a.name as account_name, r.frequency
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        LEFT JOIN recurring_transactions r ON t.recurring_id = r.id
        WHERE 1=1
    '''
    params = []
    
    if account_id:
        query += ' AND t.account_id = ?'
        params.append(account_id)
    
    if category:
        query += ' AND t.category = ?'
        params.append(category)
    
    if trans_type:
        query += ' AND t.type = ?'
        params.append(trans_type)
    
    if date_from:
        query += ' AND t.date >= ?'
        params.append(date_from)
    
    query += ' ORDER BY t.date DESC, t.id DESC LIMIT 100'
    
    transactions = db.execute(query, params).fetchall()
    db.close()
    return jsonify([dict(row) for row in transactions])

@app.route('/api/transactions/<int:id>', methods=['PUT'])
def update_transaction(id):
    """Update a transaction"""
    db = get_db()
    data = request.json
    
    # Get current transaction details
    current = db.execute('SELECT account_id, amount, type FROM transactions WHERE id = ?', (id,)).fetchone()
    if not current:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Calculate balance adjustments
    old_amount = current['amount']
    old_account_id = current['account_id']
    old_type = current['type']
    
    # Handle transfer updates (simplified - just update the single transaction)
    if data.get('type') == 'transfer' and data.get('transfer_account_id'):
        # For transfer edits, we'll update this transaction and let the user handle the paired transaction separately
        # This is a simplified approach - in a full implementation, you'd want to track paired transactions
        transfer_account_id = data['transfer_account_id']
        amount = abs(data['amount'])
        
        # Determine if this is the source or destination transaction
        if old_amount < 0:  # This was the source transaction
            new_amount = -amount
            # Set payee to destination account name
            dest_account = db.execute('SELECT name FROM accounts WHERE id = ?', (transfer_account_id,)).fetchone()
            payee = dest_account['name'] if dest_account else 'Transfer'
        else:  # This was the destination transaction  
            new_amount = amount
            # Set payee to source account name
            source_account = db.execute('SELECT name FROM accounts WHERE id = ?', (data['account_id'],)).fetchone()
            payee = source_account['name'] if source_account else 'Transfer'
        
        data['payee'] = payee
    else:
        # Regular transaction
        if data['type'] == 'expense':
            new_amount = -abs(data['amount'])
        else:
            new_amount = abs(data['amount'])
    
    new_account_id = data['account_id']
    
    # Update transaction
    db.execute('''
        UPDATE transactions 
        SET account_id = ?, amount = ?, date = ?, type = ?, payee = ?, category = ?, notes = ?
        WHERE id = ?
    ''', (
        new_account_id, new_amount, data['date'], data['type'],
        data.get('payee'), data.get('category'), data.get('notes'), id
    ))
    
    # Adjust account balances
    if old_account_id == new_account_id:
        # Same account, just adjust the difference
        balance_diff = new_amount - old_amount
        db.execute(
            'UPDATE accounts SET balance = balance + ? WHERE id = ?',
            (balance_diff, old_account_id)
        )
    else:
        # Different accounts, reverse old and apply new
        db.execute(
            'UPDATE accounts SET balance = balance - ? WHERE id = ?',
            (old_amount, old_account_id)
        )
        db.execute(
            'UPDATE accounts SET balance = balance + ? WHERE id = ?',
            (new_amount, new_account_id)
        )
    
    db.commit()
    db.close()
    return jsonify({'message': 'Transaction updated'})

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    """Delete a transaction"""
    db = get_db()
    
    # Get transaction details
    trans = db.execute('SELECT account_id, amount FROM transactions WHERE id = ?', (id,)).fetchone()
    if trans:
        # Delete transaction
        db.execute('DELETE FROM transactions WHERE id = ?', (id,))
        # Update account balance
        db.execute(
            'UPDATE accounts SET balance = balance - ? WHERE id = ?',
            (trans['amount'], trans['account_id'])
        )
        db.commit()
    
    db.close()
    return jsonify({'message': 'Transaction deleted'})

@app.route('/api/recurring', methods=['GET'])
def get_recurring():
    """Get all recurring transactions"""
    db = get_db()
    recurring = db.execute('''
        SELECT r.*, a.name as account_name,
        CASE 
            WHEN r.frequency = 'daily' THEN date(r.last_processed, '+1 day')
            WHEN r.frequency = 'weekly' THEN date(r.last_processed, '+7 days')
            WHEN r.frequency = 'biweekly' THEN date(r.last_processed, '+14 days')
            WHEN r.frequency = 'monthly' THEN date(r.last_processed, '+1 month')
            WHEN r.frequency = 'quarterly' THEN date(r.last_processed, '+3 months')
            WHEN r.frequency = 'yearly' THEN date(r.last_processed, '+1 year')
        END as next_date
        FROM recurring_transactions r
        JOIN accounts a ON r.account_id = a.id
        WHERE r.is_active = 1
    ''').fetchall()
    db.close()
    return jsonify([dict(row) for row in recurring])

@app.route('/api/recurring/<int:id>', methods=['DELETE'])
def delete_recurring(id):
    """Delete (deactivate) a recurring transaction"""
    db = get_db()
    db.execute('UPDATE recurring_transactions SET is_active = 0 WHERE id = ?', (id,))
    db.commit()
    db.close()
    return jsonify({'message': 'Recurring transaction deleted'})

@app.route('/api/recurring/process', methods=['POST'])
def process_recurring():
    """Process due recurring transactions"""
    db = get_db()
    today = datetime.now().date()
    processed = 0
    
    recurring = db.execute('''
        SELECT * FROM recurring_transactions 
        WHERE is_active = 1 AND (end_date IS NULL OR end_date >= ?)
    ''', (today,)).fetchall()
    
    for r in recurring:
        # Calculate next due date
        last_date = datetime.strptime(r['last_processed'], '%Y-%m-%d').date()
        next_date = last_date
        
        if r['frequency'] == 'daily':
            next_date = last_date + timedelta(days=1)
        elif r['frequency'] == 'weekly':
            next_date = last_date + timedelta(weeks=1)
        elif r['frequency'] == 'biweekly':
            next_date = last_date + timedelta(weeks=2)
        elif r['frequency'] == 'monthly':
            # Handle month boundaries properly
            if last_date.month == 12:
                next_date = last_date.replace(year=last_date.year + 1, month=1)
            else:
                next_date = last_date.replace(month=last_date.month + 1)
        elif r['frequency'] == 'quarterly':
            month = last_date.month + 3
            year = last_date.year
            if month > 12:
                month = month - 12
                year = year + 1
            next_date = last_date.replace(year=year, month=month)
        elif r['frequency'] == 'yearly':
            next_date = last_date.replace(year=last_date.year + 1)
        
        if next_date <= today:
            # Create transaction
            db.execute('''
                INSERT INTO transactions 
                (account_id, amount, date, type, payee, category, notes, recurring_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r['account_id'], r['amount'], next_date, r['type'],
                r['payee'], r['category'], r['notes'], r['id']
            ))
            
            # Update account balance
            db.execute(
                'UPDATE accounts SET balance = balance + ? WHERE id = ?',
                (r['amount'], r['account_id'])
            )
            
            # Update last processed date
            db.execute(
                'UPDATE recurring_transactions SET last_processed = ? WHERE id = ?',
                (next_date, r['id'])
            )
            
            processed += 1
    
    db.commit()
    db.close()
    
    message = f'Processed {processed} recurring transaction(s)' if processed > 0 else 'No recurring transactions are due'
    return jsonify({'message': message, 'processed': processed})

@app.route('/api/analytics/stats')
def get_stats():
    """Get financial statistics with filters"""
    db = get_db()
    
    # Get query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    # Total balance (always from all accounts for now)
    if account_types:
        total = db.execute(
            f'SELECT SUM(balance) FROM accounts WHERE type IN ({",".join(["?" for _ in account_types])})',
            account_types
        ).fetchone()[0] or 0
    else:
        total = db.execute('SELECT SUM(balance) FROM accounts').fetchone()[0] or 0
    
    # Build date and account type filters
    date_filter = ''
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
    
    account_filter = ''
    if account_types:
        account_filter = f' AND a.type IN ({",".join(["?" for _ in account_types])})'
        params_income.extend(account_types)
        params_expense.extend(account_types)
    
    # Income query (exclude transfers)
    income_query = f'''
        SELECT SUM(t.amount) FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE t.type = 'income'{date_filter}{account_filter}
    '''
    
    # Expense query (exclude transfers)
    expense_query = f'''
        SELECT SUM(t.amount) FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE t.type = 'expense'{date_filter}{account_filter}
    '''
    
    income = db.execute(income_query, params_income).fetchone()[0] or 0
    expenses = abs(db.execute(expense_query, params_expense).fetchone()[0] or 0)
    
    db.close()
    
    return jsonify({
        'total_balance': total,
        'monthly_income': income,
        'monthly_expenses': expenses,
        'net_monthly': income - expenses
    })

@app.route('/api/analytics/charts')
def get_chart_data():
    """Get data for charts with filters"""
    db = get_db()
    
    # Get query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    # Build filters
    date_filter = ''
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
    
    account_filter = ''
    if account_types:
        account_filter = f' AND a.type IN ({",".join(["?" for _ in account_types])})'
        params.extend(account_types)
    
    # Category spending (exclude transfers)
    category_query = f'''
        SELECT t.category, SUM(ABS(t.amount)) as total
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE t.type = 'expense' AND t.category IS NOT NULL{date_filter}{account_filter}
        GROUP BY t.category
        ORDER BY total DESC
    '''
    categories = db.execute(category_query, params).fetchall()
    
    category_data = {
        'labels': [c['category'] for c in categories],
        'datasets': [{
            'data': [c['total'] for c in categories],
            'backgroundColor': [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
            ][:len(categories)]
        }]
    }
    
    # Monthly trend (filtered, exclude transfers)
    trend_query = f'''
        SELECT 
            strftime('%Y-%m', t.date) as month,
            SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) as income,
            SUM(CASE WHEN t.type = 'expense' THEN ABS(t.amount) ELSE 0 END) as expenses
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE t.type != 'transfer'{date_filter}{account_filter}
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    '''
    trends = db.execute(trend_query, params).fetchall()
    
    trends = list(reversed(trends))
    trend_data = {
        'labels': [t['month'] for t in trends],
        'datasets': [
            {
                'label': 'Income',
                'data': [t['income'] for t in trends],
                'borderColor': '#36A2EB',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'tension': 0.4
            },
            {
                'label': 'Expenses',
                'data': [t['expenses'] for t in trends],
                'borderColor': '#FF6384',
                'backgroundColor': 'rgba(255, 99, 132, 0.1)',
                'tension': 0.4
            }
        ]
    }
    
    # Account balances (filtered by type)
    if account_types:
        account_query = f'SELECT name, balance FROM accounts WHERE type IN ({",".join(["?" for _ in account_types])}) ORDER BY balance DESC'
        accounts = db.execute(account_query, account_types).fetchall()
    else:
        accounts = db.execute('SELECT name, balance FROM accounts ORDER BY balance DESC').fetchall()
    
    account_data = {
        'labels': [a['name'] for a in accounts],
        'datasets': [{
            'label': 'Balance',
            'data': [a['balance'] for a in accounts],
            'backgroundColor': ['#36A2EB' if a['balance'] >= 0 else '#FF6384' for a in accounts]
        }]
    }
    
    # Category trends over time (exclude transfers)
    category_trend_query = f'''
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
    
    category_trends = db.execute(category_trend_query, params).fetchall()
    
    # Organize data by category
    category_data_by_month = {}
    months = set()
    categories = set()
    
    for row in category_trends:
        month = row['month']
        category = row['category']
        total = row['total']
        
        months.add(month)
        categories.add(category)
        
        if category not in category_data_by_month:
            category_data_by_month[category] = {}
        category_data_by_month[category][month] = total
    
    # Convert to chart format
    sorted_months = sorted(list(months))[-6:]  # Last 6 months
    # Show all categories, not just top 5
    all_categories = sorted(list(categories))
    
    category_trend_data = {
        'labels': sorted_months,
        'datasets': []
    }
    
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384']
    
    for i, category in enumerate(all_categories):
        data = []
        for month in sorted_months:
            data.append(category_data_by_month.get(category, {}).get(month, 0))
        
        category_trend_data['datasets'].append({
            'label': category,
            'data': data,
            'borderColor': colors[i % len(colors)],
            'backgroundColor': colors[i % len(colors)] + '20',
            'tension': 0.4
        })
    
    db.close()
    
    return jsonify({
        'category': category_data,
        'trend': trend_data,
        'accounts': account_data,
        'category_trends': category_trend_data
    })

@app.route('/api/database/info')
def database_info():
    """Get database information"""
    if os.path.exists(app.config['DATABASE']):
        size = os.path.getsize(app.config['DATABASE'])
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.2f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.2f} MB"
    else:
        size_str = "Database not found"
    
    return jsonify({'size': size_str})

@app.route('/api/export')
def export_database():
    """Export the database file"""
    return send_file(
        app.config['DATABASE'],
        as_attachment=True,
        download_name=f'money_tracker_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    )

@app.route('/api/import', methods=['POST'])
def import_database():
    """Import a database file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.db'):
        return jsonify({'error': 'File must be a .db file'}), 400
    
    try:
        # Create backup of current database
        if os.path.exists(app.config['DATABASE']):
            backup_name = f"money_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            os.rename(app.config['DATABASE'], backup_name)
            print(f"Current database backed up as: {backup_name}")
        
        # Save the uploaded file as the new database
        file.save(app.config['DATABASE'])
        
        # Verify the database is valid by trying to connect
        test_db = sqlite3.connect(app.config['DATABASE'])
        test_db.execute('SELECT name FROM sqlite_master WHERE type="table"')
        test_db.close()
        
        return jsonify({'message': 'Database imported successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to import database: {str(e)}'}), 500

@app.route('/api/export/csv')
def export_csv():
    """Export transactions to CSV format"""
    db = get_db()
    
    # Get all transactions with account names
    transactions = db.execute('''
        SELECT 
            a.name as Account,
            t.date as Date,
            COALESCE(t.payee, '') as Payee,
            COALESCE(t.notes, '') as Notes,
            COALESCE(t.category, '') as Category,
            t.amount as Amount
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        ORDER BY t.date DESC, t.id DESC
    ''').fetchall()
    
    db.close()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Account', 'Date', 'Payee', 'Notes', 'Category', 'Amount'])
    
    # Write data
    for row in transactions:
        writer.writerow([row['Account'], row['Date'], row['Payee'], row['Notes'], row['Category'], row['Amount']])
    
    # Convert to bytes
    csv_data = output.getvalue().encode('utf-8')
    output.close()
    
    # Return as file download
    return send_file(
        io.BytesIO(csv_data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'money_tracker_transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/api/import/csv', methods=['POST'])
def import_csv():
    """Import transactions from CSV format"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File must be a .csv file'}), 400
    
    try:
        db = get_db()
        
        # Read CSV content
        csv_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        imported_count = 0
        skipped_count = 0
        
        # Get existing accounts for mapping
        accounts = {row['name']: row['id'] for row in db.execute('SELECT id, name FROM accounts').fetchall()}
        
        # Track payees and categories for bulk insert
        payees_to_add = set()
        categories_to_add = set()
        
        # First pass: collect all rows to detect transfers
        all_rows = []
        for row in csv_reader:
            all_rows.append(row)
        
        # Group by date and amount to detect transfers
        transfer_pairs = {}
        for i, row in enumerate(all_rows):
            try:
                account_name = row.get('Account', '').strip()
                date = row.get('Date', '').strip()
                payee = row.get('Payee', '').strip()
                amount = float(row.get('Amount', 0))
                
                if not account_name or not date or amount == 0:
                    continue
                
                # Look for opposite amount on same date with matching payee that is an account name
                key = f"{date}_{abs(amount)}"
                if key not in transfer_pairs:
                    transfer_pairs[key] = []
                transfer_pairs[key].append((i, row, account_name, payee, amount))
            except:
                continue
        
        # Identify transfers
        detected_transfers = set()
        for key, candidates in transfer_pairs.items():
            if len(candidates) >= 2:
                for i, (idx1, row1, acc1, payee1, amt1) in enumerate(candidates):
                    for idx2, row2, acc2, payee2, amt2 in candidates[i+1:]:
                        # Check if amounts are opposite and payees match account names
                        if (amt1 == -amt2 and 
                            ((payee1 == acc2 and payee2 == acc1) or 
                             (payee1 == acc2 and not payee2) or 
                             (payee2 == acc1 and not payee1))):
                            detected_transfers.add(idx1)
                            detected_transfers.add(idx2)
        
        # Second pass: import transactions
        for i, row in enumerate(all_rows):
            try:
                # Map CSV columns (case-insensitive)
                account_name = row.get('Account', '').strip()
                date = row.get('Date', '').strip()
                payee = row.get('Payee', '').strip() or None
                notes = row.get('Notes', '').strip() or None
                category = row.get('Category', '').strip() or None
                amount = float(row.get('Amount', 0))
                
                # Skip empty rows
                if not account_name or not date or amount == 0:
                    skipped_count += 1
                    continue
                
                # Collect payees and categories
                if payee:
                    payees_to_add.add(payee)
                if category:
                    categories_to_add.add(category)
                
                # Find or create account
                account_id = None
                if account_name in accounts:
                    account_id = accounts[account_name]
                else:
                    # Create new account
                    cursor = db.execute(
                        'INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)',
                        (account_name, 'checking', 0)
                    )
                    account_id = cursor.lastrowid
                    accounts[account_name] = account_id
                
                # Determine transaction type
                if i in detected_transfers:
                    trans_type = 'transfer'
                else:
                    trans_type = 'income' if amount > 0 else 'expense'
                
                # Insert transaction
                db.execute('''
                    INSERT INTO transactions 
                    (account_id, amount, date, type, payee, category, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (account_id, amount, date, trans_type, payee, category, notes))
                
                # Update account balance
                db.execute(
                    'UPDATE accounts SET balance = balance + ? WHERE id = ?',
                    (amount, account_id)
                )
                
                imported_count += 1
                
            except (ValueError, KeyError) as e:
                skipped_count += 1
                continue
        
        # Bulk insert payees and categories
        for payee in payees_to_add:
            try:
                db.execute('INSERT OR IGNORE INTO payees (name) VALUES (?)', (payee,))
            except:
                pass
        
        for category in categories_to_add:
            try:
                db.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
            except:
                pass
        
        db.commit()
        db.close()
        
        message = f'Successfully imported {imported_count} transactions'
        if skipped_count > 0:
            message += f', skipped {skipped_count} invalid rows'
        
        return jsonify({
            'message': message,
            'imported': imported_count,
            'skipped': skipped_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to import CSV: {str(e)}'}), 500

@app.route('/api/analytics/category/<category>')
def get_category_transactions(category):
    """Get transactions for a specific category with filters"""
    db = get_db()
    
    # Get query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    # Build filters
    params = [category]
    date_filter = ''
    account_filter = ''
    
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
        account_filter = f' AND a.type IN ({",".join(["?" for _ in account_types])})'
        params.extend(account_types)
    
    query = f'''
        SELECT t.*, a.name as account_name
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE t.category = ?{date_filter}{account_filter}
        ORDER BY t.date DESC, t.id DESC
    '''
    
    transactions = db.execute(query, params).fetchall()
    db.close()
    
    return jsonify([dict(row) for row in transactions])

def run_desktop_app():
    """Run the app in a desktop window using webview"""
    try:
        import webview
        
        def start_flask():
            app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
        
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        
        # Wait for Flask to start
        time.sleep(2)
        
        # Create and start the webview window
        webview.create_window(
            title='💰 Money Tracker',
            url='http://127.0.0.1:5000',
            width=1400,
            height=900,
            min_size=(800, 600),
            resizable=True
        )
        webview.start(debug=False)
        
    except ImportError:
        print("❌ Error: webview package not installed")
        print("📦 Install it with: pip install pywebview")
        print("🔄 Falling back to browser mode...")
        run_browser_app()

def run_browser_app():
    """Run the app and open in default browser"""
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:5000')
    
    # Start browser opener in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run Flask app
    app.run(debug=False, host='0.0.0.0', port=5000)

def run_headless():
    """Run the app in headless mode (no GUI)"""
    print("\n" + "="*50)
    print("💰 Money Tracker - Headless Mode")
    print("="*50)
    print("\n✅ Server running at: http://localhost:5000")
    print("🔗 API available at: http://localhost:5000/api/")
    print("\n📋 Available endpoints:")
    print("  • GET  /api/accounts")
    print("  • POST /api/accounts")
    print("  • GET  /api/transactions")
    print("  • POST /api/transactions")
    print("  • GET  /api/recurring")
    print("  • GET  /api/analytics/stats")
    print("  • GET  /api/analytics/charts")
    print("  • GET  /api/export")
    print("\n💡 Access the web interface from any browser")
    print("🛑 Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)

def print_startup_info():
    """Print startup information"""
    print("\n" + "="*50)
    print("💰 Money Tracker Flask Server")
    print("="*50)
    print("\n📊 Features:")
    print("  • Real SQLite database (money_tracker.db)")
    print("  • Recurring transactions")
    print("  • Multiple account support")
    print("  • Analytics and charts")
    print("  • Data export functionality")
    print("\n💡 Tips:")
    print("  • Data persists between sessions")
    print("  • Access from any device on your network")
    print("  • Database file: money_tracker.db")

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Money Tracker - Personal Finance Manager')
    parser.add_argument('--mode', choices=['window', 'browser', 'headless'], 
                       default='browser',
                       help='Run mode: window (desktop app), browser (opens browser), headless (no GUI)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to run the server on (default: 5000)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    
    args = parser.parse_args()
    
    # Initialize database on first run
    if not os.path.exists(app.config['DATABASE']):
        print("Creating new database...")
        init_db()
        print("Database initialized (empty)")
    else:
        print(f"Using existing database: {app.config['DATABASE']}")
    
    # Update Flask config with command line args
    if hasattr(args, 'port'):
        port = args.port
    else:
        port = 5000
    
    # Run based on selected mode
    if args.mode == 'window':
        print_startup_info()
        print("\n🖥️  Starting in Desktop Window mode...")
        print("="*50 + "\n")
        run_desktop_app()
        
    elif args.mode == 'browser':
        print_startup_info()
        print(f"\n🌐 Starting in Browser mode on http://localhost:{port}")
        print("🚀 Opening browser automatically...")
        print("="*50 + "\n")
        
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(f'http://localhost:{port}')
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        app.run(debug=False, host=args.host, port=port)
        
    elif args.mode == 'headless':
        run_headless()
    
    else:
        print("❌ Invalid mode specified")
        parser.print_help()