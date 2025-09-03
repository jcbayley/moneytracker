#!/usr/bin/env python3
"""
Generate realistic training/test data for MoneyTracker AI fine-tuning
Creates two types of training data matching the production prompts:
1. Query analysis: Natural language → JSON analysis
2. Summary generation: Query results → Natural language summary
"""

import sqlite3
import json
import random
import sys
import os
from datetime import datetime, timedelta
import argparse
from typing import List, Dict, Tuple

# Add the parent directory to sys.path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.ai_query import AIQueryService

class DataGenerator:
    def __init__(self, db_path="training_transactions.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        
        # Initialize AI service to use the exact same prompts as production
        self.ai_service = AIQueryService()
        
        # Realistic data for generation
        self.categories = [
            'Groceries', 'Restaurants', 'Transport', 'Utilities', 'Entertainment',
            'Shopping', 'Healthcare', 'Insurance', 'Rent', 'Bills',
            'Salary', 'Freelance', 'Investments', 'Gifts', 'Travel', 'Education', 'Subscriptions'
        ]
        
        self.payees = [
            'Tesco', 'Sainsbury', 'ASDA', 'Morrisons', 'Waitrose', 'Amazon', 'Netflix', 
            'Spotify', 'Uber', 'Shell', 'BP', 'British Gas', 'EDF', 'Thames Water', 
            'BT', 'Sky', 'Employer Ltd', 'Freelance Client', 'John Smith', 'Coffee Shop',
            'Local Restaurant', 'Train Company', 'Gym Membership', 'Insurance Co'
        ]
        
    def create_tables(self):
        """Create transaction table matching MoneyTracker schema"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                payee TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                account_id INTEGER DEFAULT 1,
                type TEXT DEFAULT 'expense',
                notes TEXT
            )
        ''')
        self.conn.commit()
    
    def generate_transactions(self, count=2000):
        """Generate realistic transactions"""
        print(f"Generating {count} realistic transactions...")
        
        # Clear existing data
        self.conn.execute("DELETE FROM transactions")
        self.conn.commit()
        
        transactions = []
        start_date = datetime.now() - timedelta(days=400)  # More data range
        end_date = datetime.now() + timedelta(days=10)     # Include future dates
        
        for _ in range(count):
            # Random date
            date_range = (end_date - start_date).days
            random_date = start_date + timedelta(days=random.randint(0, date_range))
            
            # Choose realistic category and payee
            category = random.choice(self.categories)
            payee = random.choice(self.payees)
            
            # Generate realistic amounts based on category and payee
            if category == 'Salary':
                amount = round(random.uniform(2500, 5000), 2)
                trans_type = 'income'
            elif category == 'Freelance':
                amount = round(random.uniform(300, 1500), 2)
                trans_type = 'income'
            elif category == 'Rent':
                amount = -round(random.uniform(800, 2200), 2)
                trans_type = 'expense'
            elif category == 'Groceries':
                amount = -round(random.uniform(15, 150), 2)
                trans_type = 'expense'
            elif category == 'Restaurants':
                amount = -round(random.uniform(8, 85), 2)
                trans_type = 'expense'
            elif category == 'Transport':
                if payee in ['Uber']:
                    amount = -round(random.uniform(5, 45), 2)
                elif payee in ['Shell', 'BP']:
                    amount = -round(random.uniform(25, 95), 2)
                else:  # Train, bus tickets
                    amount = -round(random.uniform(3, 35), 2)
                trans_type = 'expense'
            elif category == 'Entertainment':
                if payee in ['Netflix', 'Spotify', 'Amazon Prime', 'Disney+']:
                    amount = -round(random.uniform(7.99, 15.99), 2)  # Monthly subscriptions
                else:  # Cinema, etc
                    amount = -round(random.uniform(8, 25), 2)
                trans_type = 'expense'
            elif category == 'Utilities':
                if payee in ['British Gas', 'EDF']:
                    amount = -round(random.uniform(45, 180), 2)  # Energy bills
                elif payee in ['Thames Water']:
                    amount = -round(random.uniform(35, 85), 2)   # Water bills
                elif payee in ['BT', 'Sky']:
                    amount = -round(random.uniform(25, 65), 2)   # Internet/TV
                else:
                    amount = -round(random.uniform(20, 120), 2)
                trans_type = 'expense'
            elif category == 'Shopping':
                if payee in ['Amazon']:
                    amount = -round(random.uniform(12, 250), 2)
                else:
                    amount = -round(random.uniform(15, 180), 2)
                trans_type = 'expense'
            elif category == 'Insurance':
                amount = -round(random.uniform(25, 150), 2)  # Monthly premiums
                trans_type = 'expense'
            elif category == 'Healthcare':
                amount = -round(random.uniform(15, 85), 2)
                trans_type = 'expense'
            else:
                amount = -round(random.uniform(10, 120), 2)
                trans_type = 'expense'
            
            transactions.append({
                'date': random_date.strftime('%Y-%m-%d'),
                'payee': payee,
                'amount': amount,
                'category': category,
                'type': trans_type,
                'notes': f"Generated transaction"
            })
        
        # Insert into database
        self.conn.executemany('''
            INSERT INTO transactions (date, payee, amount, category, type, notes)
            VALUES (:date, :payee, :amount, :category, :type, :notes)
        ''', transactions)
        self.conn.commit()
        
        print(f"Created {count} transactions in database")
    
    def execute_query(self, sql: str) -> List[Dict]:
        """Execute SQL query and return results as list of dicts"""
        cursor = self.conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def create_analysis_prompt(self, query: str) -> str:
        """Use the exact same analysis prompt from production."""
        db_context = {'categories': self.categories, 'payees': self.payees}
        return self.ai_service._create_analysis_prompt(query, db_context)
    
    def create_summary_prompt(self, user_query: str, count: int, total: float, top_transactions: List[Dict]) -> str:
        """Use the exact same summary prompt from production."""
        return self.ai_service._create_summary_prompt(user_query, count, total, top_transactions)
    
    def generate_query_variations(self) -> List[Tuple[str, Dict]]:
        """Generate query variations with their expected analysis"""
        queries = []
        
        # Expense total queries with natural variations
        expense_queries = [
            ("How much did I spend this month?", {"intent": "sum", "time_period": "this_month", "transaction_type": "expense"}),
            ("how much did i spend this month", {"intent": "sum", "time_period": "this_month", "transaction_type": "expense"}),
            ("What did I spend last month?", {"intent": "sum", "time_period": "last_month", "transaction_type": "expense"}),
            ("whats my spending last month?", {"intent": "sum", "time_period": "last_month", "transaction_type": "expense"}),
            ("How much have I spent this year?", {"intent": "sum", "time_period": "this_year", "transaction_type": "expense"}),
            ("Total I've spent this year", {"intent": "sum", "time_period": "this_year", "transaction_type": "expense"}),
            ("spending this year?", {"intent": "sum", "time_period": "this_year", "transaction_type": "expense"}),
            ("My expenses last week", {"intent": "sum", "time_period": "last_week", "transaction_type": "expense"}),
            ("what did i blow last week", {"intent": "sum", "time_period": "last_week", "transaction_type": "expense"}),
            ("How much did I spend in January?", {"intent": "sum", "custom_date": "january", "transaction_type": "expense"}),
            ("january spending", {"intent": "sum", "custom_date": "january", "transaction_type": "expense"}),
            ("What did I spend in 2024-01?", {"intent": "sum", "custom_date": "2024-01", "transaction_type": "expense"}),
        ]
        
        # Category-specific queries with natural variations
        category_variations = {
            'Groceries': ['groceries', 'food', 'grocery shopping', 'supermarket'],
            'Transport': ['transport', 'travel', 'getting around', 'commuting'],
            'Restaurants': ['restaurants', 'eating out', 'takeaways', 'food delivery'],
            'Bills': ['bills', 'utilities', 'monthly bills']
        }
        
        for category in ['Groceries', 'Transport', 'Restaurants', 'Bills']:
            variations = category_variations.get(category, [category.lower()])
            for var in variations[:2]:  # Use 2 variations per category
                queries.extend([
                    (f"How much did I spend on {var} this month?", 
                     {"intent": "sum", "time_period": "this_month", "categories": [category], "transaction_type": "expense"}),
                    (f"what did i spend on {var}?", 
                     {"intent": "sum", "categories": [category], "transaction_type": "expense"}),
                    (f"Show me {var} expenses", 
                     {"intent": "search", "categories": [category], "transaction_type": "expense"}),
                    (f"my {var} spending last month", 
                     {"intent": "sum", "time_period": "last_month", "categories": [category], "transaction_type": "expense"}),
                ])
        
        # Payee-specific queries with natural variations
        for payee in ['Tesco', 'Amazon', 'Netflix', 'Uber']:
            queries.extend([
                (f"How much did I spend at {payee}?", 
                 {"intent": "sum", "payees": [payee], "transaction_type": "expense"}),
                (f"what did i pay {payee}?", 
                 {"intent": "sum", "payees": [payee], "transaction_type": "expense"}),
                (f"Show me payments to {payee}", 
                 {"intent": "search", "payees": [payee]}),
                (f"{payee} payments", 
                 {"intent": "search", "payees": [payee]}),
                (f"What did I pay {payee} this month?", 
                 {"intent": "sum", "time_period": "this_month", "payees": [payee]}),
                (f"how much to {payee} this month", 
                 {"intent": "sum", "time_period": "this_month", "payees": [payee]}),
            ])
        
        # Top expenses queries with natural variations
        queries.extend([
            ("What are my biggest expenses?", {"intent": "top", "transaction_type": "expense"}),
            ("biggest expenses", {"intent": "top", "transaction_type": "expense"}),
            ("whats my largest spending?", {"intent": "top", "transaction_type": "expense"}),
            ("Show my largest spending this month", {"intent": "top", "time_period": "this_month", "transaction_type": "expense"}),
            ("biggest spending this month", {"intent": "top", "time_period": "this_month", "transaction_type": "expense"}),
            ("Top expenses last month", {"intent": "top", "time_period": "last_month", "transaction_type": "expense"}),
            ("most expensive last month", {"intent": "top", "time_period": "last_month", "transaction_type": "expense"}),
        ])
        
        # Income queries with natural variations
        queries.extend([
            ("How much did I earn this month?", {"intent": "sum", "time_period": "this_month", "transaction_type": "income"}),
            ("what did i earn this month", {"intent": "sum", "time_period": "this_month", "transaction_type": "income"}),
            ("my income this month", {"intent": "sum", "time_period": "this_month", "transaction_type": "income"}),
            ("Total income last month", {"intent": "sum", "time_period": "last_month", "transaction_type": "income"}),
            ("earnings last month", {"intent": "sum", "time_period": "last_month", "transaction_type": "income"}),
            ("Show me my salary payments", {"intent": "search", "categories": ["Salary"], "transaction_type": "income"}),
            ("salary payments", {"intent": "search", "categories": ["Salary"], "transaction_type": "income"}),
        ])
        
        # Search queries with natural variations
        queries.extend([
            ("Show me all transactions", {"intent": "search"}),
            ("all transactions", {"intent": "search"}),
            ("show everything", {"intent": "search"}),
            ("Find all expenses", {"intent": "search", "transaction_type": "expense"}),
            ("all my expenses", {"intent": "search", "transaction_type": "expense"}),
            ("Show transactions from last week", {"intent": "search", "time_period": "last_week"}),
            ("last weeks transactions", {"intent": "search", "time_period": "last_week"}),
            ("what happened last week", {"intent": "search", "time_period": "last_week"}),
        ])
        
        queries.extend(expense_queries)
        return queries
    
    def generate_analysis_training_data(self, count=300) -> List[Dict]:
        """Generate training data for query analysis (natural language → JSON)"""
        print(f"Generating {count} query analysis training examples...")
        
        query_variations = self.generate_query_variations()
        examples = []
        
        for i in range(count):
            query_text, expected_analysis = random.choice(query_variations)
            
            # Add default values for complete analysis
            full_analysis = {
                "intent": "search",
                "time_period": None,
                "custom_date": None, 
                "categories": [],
                "payees": [],
                "transaction_type": None
            }
            full_analysis.update(expected_analysis)
            
            # Create training example
            prompt = self.create_analysis_prompt(query_text)
            response = json.dumps(full_analysis)
            
            training_text = f"{prompt}\n\n{response}"
            examples.append({"text": training_text})
        
        print(f"Generated {len(examples)} analysis training examples")
        return examples
    
    def generate_summary_training_data(self, count=200) -> List[Dict]:
        """Generate training data for summary generation (query results → summary)"""
        print(f"Generating {count} summary training examples...")
        
        examples = []
        query_variations = self.generate_query_variations()
        
        for i in range(count):
            try:
                query_text, analysis = random.choice(query_variations)
                
                # Build SQL query to get real results
                sql_query = self._build_sql_query(analysis)
                results = self.execute_query(sql_query)
                
                if not results:
                    continue  # Skip if no results
                
                # Limit results to realistic numbers (not 100s for simple queries)
                if analysis.get('intent') in ['sum', 'search'] and len(results) > 50:
                    results = results[:random.randint(5, 50)]  # More realistic result counts
                elif analysis.get('intent') == 'top' and len(results) > 20:
                    results = results[:random.randint(3, 20)]
                
                # Calculate summary stats
                count_tx = len(results)
                total = sum(abs(tx['amount']) for tx in results)
                top_transactions = sorted(results, key=lambda x: abs(x['amount']), reverse=True)[:3]
                
                # Generate realistic summary response
                if analysis.get('intent') == 'sum':
                    if analysis.get('transaction_type') == 'expense':
                        summary = f"You spent £{total:.2f} across {count_tx} transactions."
                    elif analysis.get('transaction_type') == 'income':
                        summary = f"You received £{total:.2f} in income from {count_tx} transactions."
                    else:
                        summary = f"Total amount: £{total:.2f} from {count_tx} transactions."
                elif analysis.get('intent') == 'top':
                    if top_transactions:
                        top_tx = top_transactions[0]
                        summary = f"Your largest expense was £{abs(top_tx['amount']):.2f} to {top_tx['payee']} on {top_tx['date']}."
                    else:
                        summary = f"Found {count_tx} transactions."
                else:  # search, count, average
                    summary = f"Found {count_tx} transactions totaling £{total:.2f}."
                
                # Create training example
                prompt = self.create_summary_prompt(query_text, count_tx, total, top_transactions)
                training_text = f"{prompt}\n\n{summary}"
                examples.append({"text": training_text})
                
            except Exception as e:
                print(f"Error generating summary example {i}: {e}")
                continue
        
        print(f"Generated {len(examples)} summary training examples")
        return examples
    
    def _build_sql_query(self, analysis: Dict) -> str:
        """Build SQL query from analysis (simplified version)"""
        query = "SELECT * FROM transactions WHERE 1=1"
        
        # Time filter
        if analysis.get('time_period') == 'this_month':
            query += " AND date >= date('now', 'start of month')"
        elif analysis.get('time_period') == 'last_month':
            query += " AND date >= date('now', 'start of month', '-1 month') AND date < date('now', 'start of month')"
        elif analysis.get('time_period') == 'this_year':
            query += " AND date >= date('now', 'start of year')"
        elif analysis.get('time_period') == 'last_week':
            query += " AND date >= date('now', '-7 days')"
        
        # Custom date (simplified)
        if analysis.get('custom_date'):
            if 'january' in analysis['custom_date'].lower():
                query += " AND date >= '2025-01-01' AND date <= '2025-01-31'"
            elif '2024-01' in analysis['custom_date']:
                query += " AND date >= '2024-01-01' AND date <= '2024-01-31'"
            elif 'february' in analysis['custom_date'].lower():
                query += " AND date >= '2025-02-01' AND date <= '2025-02-31'"
            elif '2024-10' in analysis['custom_date']:
                query += " AND date >= '2024-10-01' AND date <= '2024-10-31'"
        
        # Transaction type
        if analysis.get('transaction_type'):
            query += f" AND type = '{analysis['transaction_type']}'"
        
        # Categories
        if analysis.get('categories'):
            conditions = [f"category LIKE '%{cat}%'" for cat in analysis['categories']]
            query += f" AND ({' OR '.join(conditions)})"
        
        # Payees
        if analysis.get('payees'):
            conditions = [f"payee LIKE '%{payee}%'" for payee in analysis['payees']]
            query += f" AND ({' OR '.join(conditions)})"
        
        # Ordering
        if analysis.get('intent') == 'top':
            query += " ORDER BY ABS(amount) DESC"
        else:
            query += " ORDER BY date DESC"
        
        return query
    
    def generate_test_cases(self, count=50) -> List[Dict]:
        """Generate test cases matching training data structure"""
        print(f"Generating {count} test cases (both analysis and summary tasks)...")
        
        query_variations = self.generate_query_variations()
        test_cases = []
        
        # Generate half analysis test cases, half summary test cases
        analysis_count = count // 2
        summary_count = count - analysis_count
        
        # Generate analysis test cases (Natural Language → JSON)
        for i in range(analysis_count):
            try:
                query_text, expected_analysis = random.choice(query_variations)
                
                # Add default values for complete analysis
                full_analysis = {
                    "intent": "search",
                    "time_period": None,
                    "custom_date": None, 
                    "categories": [],
                    "payees": [],
                    "transaction_type": None
                }
                full_analysis.update(expected_analysis)
                
                # Create test case matching analysis training format
                prompt = self.create_analysis_prompt(query_text)
                expected_response = json.dumps(full_analysis)
                
                test_cases.append({
                    "id": f"analysis_test_{i+1}",
                    "task_type": "analysis",
                    "prompt": prompt,
                    "expected_response": expected_response,
                    "query": query_text,
                    "expected_analysis": full_analysis
                })
                
            except Exception as e:
                print(f"Error generating analysis test case {i}: {e}")
                continue
        
        # Generate summary test cases (Query Results → Natural Language)
        for i in range(summary_count):
            try:
                query_text, analysis = random.choice(query_variations)
                
                # Execute query to get real results
                sql_query = self._build_sql_query(analysis)
                results = self.execute_query(sql_query)
                
                if not results:
                    continue
                
                # Limit to realistic result counts
                if len(results) > 30:
                    results = results[:random.randint(5, 30)]
                
                count_tx = len(results)
                total = sum(abs(tx['amount']) for tx in results)
                top_transactions = sorted(results, key=lambda x: abs(x['amount']), reverse=True)[:3]
                
                # Generate expected summary
                if analysis.get('intent') == 'sum':
                    if analysis.get('transaction_type') == 'expense':
                        expected_summary = f"You spent £{total:.2f} across {count_tx} transactions."
                    elif analysis.get('transaction_type') == 'income':
                        expected_summary = f"You received £{total:.2f} in income from {count_tx} transactions."
                    else:
                        expected_summary = f"Total amount: £{total:.2f} from {count_tx} transactions."
                elif analysis.get('intent') == 'top':
                    if top_transactions:
                        top_tx = top_transactions[0]
                        expected_summary = f"Your largest expense was £{abs(top_tx['amount']):.2f} to {top_tx['payee']} on {top_tx['date']}."
                    else:
                        expected_summary = f"Found {count_tx} transactions."
                else:  # search, count, average
                    expected_summary = f"Found {count_tx} transactions totaling £{total:.2f}."
                
                # Create test case matching summary training format
                prompt = self.create_summary_prompt(query_text, count_tx, total, top_transactions)
                
                test_cases.append({
                    "id": f"summary_test_{i+1}",
                    "task_type": "summary",
                    "prompt": prompt,
                    "expected_response": expected_summary,
                    "query": query_text,
                    "result_count": count_tx,
                    "total_amount": total
                })
                
            except Exception as e:
                print(f"Error generating summary test case {i}: {e}")
                continue
        
        print(f"Generated {len(test_cases)} test cases ({analysis_count} analysis, {len(test_cases)-analysis_count} summary)")
        return test_cases

def main():
    parser = argparse.ArgumentParser(description='Generate training and test data matching production prompts')
    parser.add_argument('--transactions', type=int, default=1500,
                       help='Number of transactions to generate')
    parser.add_argument('--analysis-examples', type=int, default=250,
                       help='Number of query analysis examples')
    parser.add_argument('--summary-examples', type=int, default=150,
                       help='Number of summary generation examples')
    parser.add_argument('--test-cases', type=int, default=50,
                       help='Number of test cases to generate')
    parser.add_argument('--db-path', type=str, default='training_transactions.db',
                       help='SQLite database path')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = DataGenerator(args.db_path)
    
    # Generate synthetic transactions
    generator.generate_transactions(args.transactions)
    
    # Generate analysis training data (Natural Language → JSON)
    # Task 1: "Parse financial query to JSON..." → JSON response
    analysis_examples = generator.generate_analysis_training_data(args.analysis_examples)
    
    # Generate summary training data (Query Results → Natural Language)
    # Task 2: "Answer user's financial question..." → Natural language response
    summary_examples = generator.generate_summary_training_data(args.summary_examples)
    
    # Combine both tasks in single training file
    # Model learns task switching based on prompt patterns
    all_examples = analysis_examples + summary_examples
    random.shuffle(all_examples)  # Mix the tasks for better learning
    
    # Save training data as JSONL
    with open('training_data.jsonl', 'w') as f:
        for example in all_examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"Training data saved to: training_data.jsonl")
    print(f"Total examples: {len(all_examples)} (Analysis: {len(analysis_examples)}, Summary: {len(summary_examples)})")
    
    # Generate test cases
    test_cases = generator.generate_test_cases(args.test_cases)
    
    # Save test data as JSON
    with open('test_data.json', 'w') as f:
        json.dump(test_cases, f, indent=2)
    
    print(f"Test data saved to: test_data.json")
    print(f"Database created at: {args.db_path}")
    
    # Show sample data
    print("\n--- Sample Analysis Training Example ---")
    if analysis_examples:
        print(analysis_examples[0]['text'][:400] + "...")
    
    print("\n--- Sample Summary Training Example ---")
    if summary_examples:
        print(summary_examples[0]['text'][:400] + "...")

if __name__ == "__main__":
    main()