#!/usr/bin/env python3
"""
Training Data Generation Script for MoneyTracker AI Query Fine-tuning

This script generates synthetic training data for fine-tuning a model to:
1. Generate SQL queries from natural language questions
2. Summarize query results effectively

The generated data follows the format expected by the qlora_finetune.py script.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import argparse
import os

class TrainingDataGenerator:
    def __init__(self):
        # Sample data for generating realistic examples
        self.accounts = ["Current Account", "Savings Account", "Investment Account", "ISA"]
        self.categories = [
            "Groceries", "Restaurants", "Transportation", "Utilities", "Entertainment", 
            "Shopping", "Healthcare", "Insurance", "Education", "Travel", "Bills",
            "Salary", "Freelance", "Investments", "Gifts", "Subscriptions", "Fitness"
        ]
        self.payees = [
            "Tesco", "Sainsburys", "Amazon", "Netflix", "Spotify", "Uber", "Shell",
            "British Gas", "Thames Water", "Council Tax", "Employer Ltd", "John Smith",
            "Coffee Shop", "Local Restaurant", "Train Company", "Gym Membership",
            "Insurance Co", "Mobile Network", "Internet Provider", "Freelance Client"
        ]
        self.projects = ["Holiday Spain", "Home Renovation", "Wedding", "Car Purchase", "Christmas"]
        
        # Query templates for different intents
        self.query_templates = {
            "search": [
                "Show me all transactions",
                "Find transactions from {payee}",
                "What did I spend on {category}",
                "Show me {transaction_type} transactions",
                "Find all transactions in {time_period}",
                "Show transactions for {project}",
                "What transactions were on {date}"
            ],
            "sum": [
                "How much did I spend in total",
                "Total spent on {category}",
                "How much did I spend at {payee}",
                "Total {transaction_type} in {time_period}",
                "Sum of {project} expenses",
                "How much was spent on {date}"
            ],
            "top": [
                "Show my biggest expenses",
                "Largest transactions",
                "Top spending on {category}",
                "Biggest {transaction_type} transactions",
                "Highest amounts in {time_period}"
            ],
            "average": [
                "Average spending per month",
                "Average {category} spending",
                "What's my average {transaction_type}",
                "Average amount spent at {payee}"
            ],
            "count": [
                "How many transactions",
                "Count of {category} purchases",
                "Number of {transaction_type} transactions",
                "How many times did I shop at {payee}"
            ]
        }
        
        self.time_periods = ["today", "yesterday", "last_week", "this_month", "last_month", "this_year"]
        self.transaction_types = ["expense", "income", "transfer"]

    def generate_sample_transactions(self, count: int = 50) -> List[Dict]:
        """Generate sample transaction data for context"""
        transactions = []
        base_date = datetime.now() - timedelta(days=365)
        
        for i in range(count):
            # Random date within last year
            random_days = random.randint(0, 365)
            transaction_date = (base_date + timedelta(days=random_days)).strftime("%Y-%m-%d")
            
            transaction_type = random.choice(self.transaction_types)
            
            # Generate realistic amounts based on type
            if transaction_type == "expense":
                amount = -round(random.uniform(5.0, 500.0), 2)
            elif transaction_type == "income":
                amount = round(random.uniform(100.0, 3000.0), 2)
            else:  # transfer
                amount = round(random.uniform(50.0, 1000.0), 2)
            
            transactions.append({
                "id": i + 1,
                "account_id": random.randint(1, 4),
                "account_name": random.choice(self.accounts),
                "amount": amount,
                "date": transaction_date,
                "type": transaction_type,
                "payee": random.choice(self.payees),
                "category": random.choice(self.categories),
                "project": random.choice(self.projects) if random.random() < 0.3 else None,
                "notes": "Sample transaction"
            })
        
        return transactions

    def generate_sql_query(self, analysis: Dict, transactions: List[Dict]) -> Tuple[str, List]:
        """Generate SQL query and params based on analysis"""
        query = "SELECT t.*, a.name as account_name FROM transactions t JOIN accounts a ON t.account_id = a.id WHERE 1=1"
        params = []
        
        # Time filter
        if analysis.get('time_period'):
            if analysis['time_period'] == 'this_month':
                query += " AND t.date >= ? AND t.date <= ?"
                params.extend(['2024-01-01', '2024-01-31'])
            elif analysis['time_period'] == 'last_week':
                query += " AND t.date >= ? AND t.date <= ?"
                params.extend(['2024-01-01', '2024-01-07'])
        
        # Custom date filter
        if analysis.get('custom_date'):
            query += " AND t.date >= ? AND t.date <= ?"
            params.extend([analysis['custom_date'], analysis['custom_date']])
        
        # Transaction type filter
        if analysis.get('transaction_type'):
            query += " AND t.type = ?"
            params.append(analysis['transaction_type'])
        
        # Category filter
        if analysis.get('categories'):
            placeholders = ' OR '.join(['t.category LIKE ?' for _ in analysis['categories']])
            query += f" AND ({placeholders})"
            params.extend([f"%{cat}%" for cat in analysis['categories']])
        
        # Payee filter
        if analysis.get('payees'):
            placeholders = ' OR '.join(['t.payee LIKE ?' for _ in analysis['payees']])
            query += f" AND ({placeholders})"
            params.extend([f"%{payee}%" for payee in analysis['payees']])
        
        # Ordering based on intent
        if analysis.get('intent') == 'top':
            query += " ORDER BY ABS(t.amount) DESC LIMIT 10"
        else:
            query += " ORDER BY t.date DESC LIMIT 100"
        
        return query, params

    def filter_transactions(self, transactions: List[Dict], analysis: Dict) -> List[Dict]:
        """Filter sample transactions based on analysis to simulate query results"""
        filtered = []
        
        for tx in transactions:
            include = True
            
            # Transaction type filter
            if analysis.get('transaction_type') and tx['type'] != analysis['transaction_type']:
                include = False
            
            # Category filter
            if analysis.get('categories') and not any(cat.lower() in tx['category'].lower() for cat in analysis['categories']):
                include = False
            
            # Payee filter  
            if analysis.get('payees') and not any(payee.lower() in tx['payee'].lower() for payee in analysis['payees']):
                include = False
            
            if include:
                filtered.append(tx)
        
        # Apply intent-based sorting/limiting
        if analysis.get('intent') == 'top':
            filtered.sort(key=lambda x: abs(x['amount']), reverse=True)
            filtered = filtered[:10]
        elif analysis.get('intent') in ['sum', 'average', 'count']:
            filtered = filtered[:50]  # More data for calculations
        else:
            filtered.sort(key=lambda x: x['date'], reverse=True)
            filtered = filtered[:20]
        
        return filtered

    def generate_summary(self, query: str, analysis: Dict, results: List[Dict]) -> str:
        """Generate appropriate summary based on query intent and results"""
        if not results:
            return "No transactions found matching your query."
        
        count = len(results)
        total = sum(abs(tx['amount']) for tx in results)
        
        intent = analysis.get('intent', 'search')
        
        if intent == 'sum':
            return f"Found {count} transactions totaling £{total:.2f}."
        elif intent == 'count':
            return f"Found {count} transactions matching your criteria."
        elif intent == 'average':
            avg = total / count if count > 0 else 0
            return f"Found {count} transactions with an average amount of £{avg:.2f}."
        elif intent == 'top':
            if results:
                top_amount = abs(results[0]['amount'])
                top_payee = results[0]['payee']
                return f"Your largest transaction was £{top_amount:.2f} to {top_payee}. Found {count} total transactions."
        else:  # search
            if count <= 5:
                payees = set(tx['payee'] for tx in results[:3])
                return f"Found {count} transactions totaling £{total:.2f}, including payments to {', '.join(list(payees)[:2])}."
            else:
                return f"Found {count} transactions totaling £{total:.2f}."

    def create_training_example(self, query: str, analysis: Dict, sql_query: str, sql_params: List, results: List[Dict], summary: str) -> str:
        """Create a formatted training example for the model"""
        
        # Format the SQL query for display
        formatted_sql = sql_query
        for param in sql_params:
            if isinstance(param, str):
                formatted_sql = formatted_sql.replace('?', f"'{param}'", 1)
            else:
                formatted_sql = formatted_sql.replace('?', str(param), 1)
        
        # Create the training text in a conversational format
        training_text = f"""User Query: {query}

Analysis: {json.dumps(analysis, indent=2)}

Generated SQL:
{formatted_sql}

Results Summary: {summary}

Found {len(results)} transactions totaling £{sum(abs(tx['amount']) for tx in results):.2f}."""

        return training_text

    def generate_training_data(self, num_examples: int = 100) -> List[Dict]:
        """Generate complete training dataset"""
        
        # Generate base transaction data
        transactions = self.generate_sample_transactions(200)
        
        training_examples = []
        
        for _ in range(num_examples):
            # Pick random intent and template
            intent = random.choice(list(self.query_templates.keys()))
            template = random.choice(self.query_templates[intent])
            
            # Create analysis structure
            analysis = {
                "intent": intent,
                "time_period": None,
                "custom_date": None,
                "categories": [],
                "payees": [],
                "transaction_type": None
            }
            
            # Fill template and analysis based on placeholders
            query = template
            
            if "{payee}" in template:
                payee = random.choice(self.payees)
                query = query.replace("{payee}", payee)
                analysis["payees"] = [payee]
            
            if "{category}" in template:
                category = random.choice(self.categories)
                query = query.replace("{category}", category)
                analysis["categories"] = [category]
            
            if "{transaction_type}" in template:
                tx_type = random.choice(self.transaction_types)
                query = query.replace("{transaction_type}", tx_type)
                analysis["transaction_type"] = tx_type
            
            if "{time_period}" in template:
                time_period = random.choice(self.time_periods)
                query = query.replace("{time_period}", time_period)
                analysis["time_period"] = time_period
            
            if "{project}" in template:
                project = random.choice(self.projects)
                query = query.replace("{project}", project)
                analysis["projects"] = [project]
            
            if "{date}" in template:
                date = "2024-01-15"
                query = query.replace("{date}", date)
                analysis["custom_date"] = date
            
            # Generate SQL and results
            sql_query, sql_params = self.generate_sql_query(analysis, transactions)
            filtered_results = self.filter_transactions(transactions, analysis)
            summary = self.generate_summary(query, analysis, filtered_results)
            
            # Create training example
            training_text = self.create_training_example(
                query, analysis, sql_query, sql_params, filtered_results, summary
            )
            
            training_examples.append({"text": training_text})
        
        return training_examples

def main():
    parser = argparse.ArgumentParser(description='Generate training data for MoneyTracker AI fine-tuning')
    parser.add_argument('--num-examples', type=int, default=500,
                       help='Number of training examples to generate')
    parser.add_argument('--output', type=str, default='training_data.jsonl',
                       help='Output file path (JSONL format)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    # Set random seed for reproducibility
    random.seed(args.seed)
    
    print(f"Generating {args.num_examples} training examples...")
    
    # Generate training data
    generator = TrainingDataGenerator()
    training_data = generator.generate_training_data(args.num_examples)
    
    # Save to JSONL format
    print(f"Saving training data to {args.output}...")
    with open(args.output, 'w') as f:
        for example in training_data:
            f.write(json.dumps(example) + '\n')
    
    print(f"Generated {len(training_data)} training examples")
    print(f"Training data saved to: {args.output}")
    print(f"\nTo fine-tune the model, run:")
    print(f"python qlora_finetune.py --model microsoft/phi-2 --data {args.output} --rank 16")
    
    # Show sample example
    if training_data:
        print(f"\n--- Sample Training Example ---")
        print(training_data[0]['text'][:500] + "..." if len(training_data[0]['text']) > 500 else training_data[0]['text'])

if __name__ == "__main__":
    main()