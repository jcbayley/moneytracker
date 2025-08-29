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
from datetime import datetime, timedelta
import argparse
from typing import List, Dict, Tuple

class DataGenerator:
    def __init__(self, db_path="training_transactions.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        
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
            
            # Generate realistic amounts
            if category == 'Salary':
                amount = round(random.uniform(2000, 6000), 2)
                trans_type = 'income'
            elif category == 'Freelance':
                amount = round(random.uniform(200, 2000), 2)
                trans_type = 'income'
            elif category == 'Rent':
                amount = -round(random.uniform(800, 2500), 2)
                trans_type = 'expense'
            elif category == 'Groceries':
                amount = -round(random.uniform(10, 200), 2)
                trans_type = 'expense'
            elif category in ['Utilities', 'Insurance', 'Bills']:
                amount = -round(random.uniform(30, 400), 2)
                trans_type = 'expense'
            else:
                amount = -round(random.uniform(5, 500), 2)
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
        """Create the exact prompt used in production for query analysis"""
        return f'''Parse financial query to JSON for sql search:
Query: "{query}"

Categories: {', '.join(self.categories[:10])}
Payees: {', '.join(self.payees[:10])}

RULES:
- Only use filters if EXPLICITLY mentioned in query
- For dates: support specific dates like "2024-01", "january", "march 2024", "2024-03-15" as custom_date
- Only filter by payee if query specifically mentions a payee name
- Only filter by category if query specifically mentions a category
- Auto-detect transaction type from keywords:
  - "expense/expenses/spent/spending/paid/cost/bill" → "expense"
  - "income/earned/salary/revenue/received" → "income" 
  - "transfer" → "transfer"

Return JSON:
{{
  "intent": "search|sum|top|average|count",
  "time_period": "today|yesterday|last_week|this_month|last_month|this_year|last_year" or null,
  "custom_date": "YYYY-MM-DD or YYYY-MM or specific date string" or null,
  "categories": ["only if explicitly mentioned"],
  "payees": ["only if explicitly mentioned"],
  "transaction_type": "income|expense|transfer" or null
}}'''
    
    def create_summary_prompt(self, user_query: str, count: int, total: float, top_transactions: List[Dict]) -> str:
        """Create the exact prompt used in production for summary generation"""
        # Format top transactions context
        top_tx_context = []
        for tx in top_transactions:
            top_tx_context.append(f"£{abs(tx['amount']):.2f} to {tx['payee']} on {tx['date']}")
        
        return f'''Answer user's financial question:
Question: "{user_query}"
Found {count} transactions, total £{total:.2f}
Top amounts: {'; '.join(top_tx_context[:2])}

Provide short direct answer:'''
    
    def generate_query_variations(self) -> List[Tuple[str, Dict]]:
        """Generate query variations with their expected analysis"""
        queries = []
        
        # Expense total queries
        expense_queries = [
            ("How much did I spend this month?", {"intent": "sum", "time_period": "this_month", "transaction_type": "expense"}),
            ("What did I spend last month?", {"intent": "sum", "time_period": "last_month", "transaction_type": "expense"}),
            ("How much have I spent this year?", {"intent": "sum", "time_period": "this_year", "transaction_type": "expense"}),
            ("Total expenses last week", {"intent": "sum", "time_period": "last_week", "transaction_type": "expense"}),
            ("How much did I spend in January?", {"intent": "sum", "custom_date": "january", "transaction_type": "expense"}),
            ("What did I spend in 2024-01?", {"intent": "sum", "custom_date": "2024-01", "transaction_type": "expense"}),
        ]
        
        # Category-specific queries
        for category in ['Groceries', 'Transport', 'Restaurants', 'Bills']:
            queries.extend([
                (f"How much did I spend on {category} this month?", 
                 {"intent": "sum", "time_period": "this_month", "categories": [category], "transaction_type": "expense"}),
                (f"Show me {category} expenses", 
                 {"intent": "search", "categories": [category], "transaction_type": "expense"}),
                (f"Total {category} spending last month", 
                 {"intent": "sum", "time_period": "last_month", "categories": [category], "transaction_type": "expense"}),
            ])
        
        # Payee-specific queries  
        for payee in ['Tesco', 'Amazon', 'Netflix', 'Uber']:
            queries.extend([
                (f"How much did I spend at {payee}?", 
                 {"intent": "sum", "payees": [payee], "transaction_type": "expense"}),
                (f"Show me payments to {payee}", 
                 {"intent": "search", "payees": [payee]}),
                (f"What did I pay {payee} this month?", 
                 {"intent": "sum", "time_period": "this_month", "payees": [payee]}),
            ])
        
        # Top expenses queries
        queries.extend([
            ("What are my biggest expenses?", {"intent": "top", "transaction_type": "expense"}),
            ("Show my largest spending this month", {"intent": "top", "time_period": "this_month", "transaction_type": "expense"}),
            ("Top expenses last month", {"intent": "top", "time_period": "last_month", "transaction_type": "expense"}),
        ])
        
        # Income queries
        queries.extend([
            ("How much did I earn this month?", {"intent": "sum", "time_period": "this_month", "transaction_type": "income"}),
            ("Total income last month", {"intent": "sum", "time_period": "last_month", "transaction_type": "income"}),
            ("Show me my salary payments", {"intent": "search", "categories": ["Salary"], "transaction_type": "income"}),
        ])
        
        # Search queries
        queries.extend([
            ("Show me all transactions", {"intent": "search"}),
            ("Find all expenses", {"intent": "search", "transaction_type": "expense"}),
            ("Show transactions from last week", {"intent": "search", "time_period": "last_week"}),
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
                query += " AND date >= '2024-01-01' AND date <= '2024-01-31'"
            elif '2024-01' in analysis['custom_date']:
                query += " AND date >= '2024-01-01' AND date <= '2024-01-31'"
        
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
            query += " ORDER BY ABS(amount) DESC LIMIT 20"
        else:
            query += " ORDER BY date DESC LIMIT 100"
        
        return query
    
    def generate_test_cases(self, count=50) -> List[Dict]:
        """Generate test cases for evaluation"""
        print(f"Generating {count} test cases...")
        
        query_variations = self.generate_query_variations()
        test_cases = []
        
        for i in range(count):
            try:
                query_text, analysis = random.choice(query_variations)
                
                # Execute query to get real results
                sql_query = self._build_sql_query(analysis)
                results = self.execute_query(sql_query)
                
                # Calculate actual results
                total = sum(abs(tx['amount']) for tx in results) if results else 0
                
                test_cases.append({
                    "id": f"test_{i+1}",
                    "query": query_text,
                    "expected_analysis": analysis,
                    "expected_sql": sql_query,
                    "expected_result": total,
                    "expected_sql_contains": ["SELECT", "FROM", "transactions"],
                    "expected_summary_contains": [f"£{total:.2f}" if total > 0 else "£0.00", str(len(results))]
                })
                
            except Exception as e:
                print(f"Error generating test case {i}: {e}")
                continue
        
        print(f"Generated {len(test_cases)} test cases")
        return test_cases

def main():
    parser = argparse.ArgumentParser(description='Generate training and test data matching production prompts')
    parser.add_argument('--transactions', type=int, default=2000,
                       help='Number of transactions to generate')
    parser.add_argument('--analysis-examples', type=int, default=300,
                       help='Number of query analysis examples')
    parser.add_argument('--summary-examples', type=int, default=200,
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
    
    # Generate analysis training data
    analysis_examples = generator.generate_analysis_training_data(args.analysis_examples)
    
    # Generate summary training data  
    summary_examples = generator.generate_summary_training_data(args.summary_examples)
    
    # Combine all training examples
    all_examples = analysis_examples + summary_examples
    
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