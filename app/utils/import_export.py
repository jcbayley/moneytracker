"""Import/Export utilities."""
import os
import io
import csv
import sqlite3
from datetime import datetime
from flask import current_app, send_file, request, jsonify
from ..database import Database
from ..models import account
from ..models import payee
from ..models import category


def get_database_info():
        """Get database file information."""
        db_path = current_app.config['DATABASE']
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.2f} MB"
        else:
            size_str = "Database not found"
        
        return {'size': size_str}
    
def export_database():
        """Export the database file."""
        db_path = current_app.config['DATABASE']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'money_tracker_backup_{timestamp}.db'
        
        return send_file(db_path, as_attachment=True, download_name=filename)
    
def import_database(file):
        """Import a database file."""
        if not file or file.filename == '':
            return {'error': 'No file selected'}, 400
        
        if not file.filename.endswith('.db'):
            return {'error': 'File must be a .db file'}, 400
        
        try:
            db_path = current_app.config['DATABASE']
            
            # Create backup of current database
            if os.path.exists(db_path):
                backup_name = f"money_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                os.rename(db_path, backup_name)
                print(f"Current database backed up as: {backup_name}")
            
            # Save the uploaded file as the new database
            file.save(db_path)
            
            # Verify the database is valid
            test_db = sqlite3.connect(db_path)
            test_db.execute('SELECT name FROM sqlite_master WHERE type="table"')
            test_db.close()
            
            return {'message': 'Database imported successfully'}, 200
            
        except Exception as e:
            return {'error': f'Failed to import database: {str(e)}'}, 500
    
def export_csv():
        """Export transactions to CSV format."""
        with Database.get_db() as db:
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
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Account', 'Date', 'Payee', 'Notes', 'Category', 'Amount'])
        
        # Write data
        for row in transactions:
            writer.writerow([row['Account'], row['Date'], row['Payee'], 
                           row['Notes'], row['Category'], row['Amount']])
        
        # Convert to bytes
        csv_data = output.getvalue().encode('utf-8')
        output.close()
        
        # Return as file download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'money_tracker_transactions_{timestamp}.csv'
        
        return send_file(
            io.BytesIO(csv_data),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )


def generate_csv_content():
    """Generate CSV content as string (for native file dialog)."""
    with Database.get_db() as db:
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
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Account', 'Date', 'Payee', 'Notes', 'Category', 'Amount'])
    
    # Write data
    for row in transactions:
        writer.writerow([row['Account'], row['Date'], row['Payee'], 
                       row['Notes'], row['Category'], row['Amount']])
    
    # Return as string
    csv_content = output.getvalue()
    output.close()
    
    return csv_content
    
def import_csv(file):
        """Import transactions from CSV format."""
        if not file or file.filename == '':
            return {'error': 'No file selected'}, 400
        
        if not file.filename.lower().endswith('.csv'):
            return {'error': 'File must be a .csv file'}, 400
        
        try:
            # Read CSV content
            csv_content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            imported_count = 0
            skipped_count = 0
            
            # Get existing accounts
            accounts = {row['name']: row['id'] for row in account.get_all()}
            
            # Track payees and categories for bulk insert
            payees_to_add = set()
            categories_to_add = set()
            
            # First pass: collect all rows and detect transfers
            all_rows = list(csv_reader)
            transfer_pairs = _detect_transfers(all_rows)
            detected_transfers = _identify_transfers(transfer_pairs)
            
            # Second pass: import transactions
            with Database.get_db() as db:
                for i, row in enumerate(all_rows):
                    try:
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
                        if account_name not in accounts:
                            account_id = account.create(account_name, 'checking', 0)
                            accounts[account_name] = account_id
                        else:
                            account_id = accounts[account_name]
                        
                        # Determine transaction type
                        trans_type = 'transfer' if i in detected_transfers else ('income' if amount > 0 else 'expense')
                        
                        # Insert transaction
                        db.execute('''
                            INSERT INTO transactions 
                            (account_id, amount, date, type, payee, category, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (account_id, amount, date, trans_type, payee, category, notes))
                        
                        # Update account balance
                        account.update_balance(account_id, amount)
                        
                        imported_count += 1
                        
                    except (ValueError, KeyError):
                        skipped_count += 1
                        continue
                
                # Bulk insert payees and categories
                payee.bulk_create(payees_to_add)
                category.bulk_create(categories_to_add)
                
                db.commit()
            
            message = f'Successfully imported {imported_count} transactions'
            if skipped_count > 0:
                message += f', skipped {skipped_count} invalid rows'
            
            return {
                'message': message,
                'imported': imported_count,
                'skipped': skipped_count
            }, 200
            
        except Exception as e:
            return {'error': f'Failed to import CSV: {str(e)}'}, 500
    
def _detect_transfers(all_rows):
        """Detect potential transfer pairs in CSV data."""
        transfer_pairs = {}
        for i, row in enumerate(all_rows):
            try:
                account_name = row.get('Account', '').strip()
                date = row.get('Date', '').strip()
                payee = row.get('Payee', '').strip()
                amount = float(row.get('Amount', 0))
                
                if not account_name or not date or amount == 0:
                    continue
                
                key = f"{date}_{abs(amount)}"
                if key not in transfer_pairs:
                    transfer_pairs[key] = []
                transfer_pairs[key].append((i, row, account_name, payee, amount))
            except:
                continue
        
        return transfer_pairs
    
def _identify_transfers(transfer_pairs):
        """Identify which transactions are transfers based on patterns."""
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
        
        return detected_transfers