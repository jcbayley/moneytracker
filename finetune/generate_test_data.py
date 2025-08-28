#!/usr/bin/env python3
"""
Test Data Generation Script for MoneyTracker AI Model Evaluation

Generates test cases with known correct outputs for:
1. Natural language -> SQL query generation
2. Results -> Summary generation

The test data includes expected outputs to measure model performance.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import argparse

class TestDataGenerator:
    def __init__(self):
        # Test categories and payees (smaller, focused set)
        self.categories = ["Groceries", "Restaurants", "Transport", "Bills", "Shopping", "Entertainment"]
        self.payees = ["Tesco", "Uber", "Netflix", "British Gas", "Amazon", "Local Cafe"]
        self.projects = ["Holiday", "Home Renovation", "Wedding"]
        self.accounts = ["Current", "Savings", "Investment"]
        
        # Test cases with expected outputs
        self.test_cases = [
            {
                "query": "How much did I spend on groceries last month?",
                "expected_analysis": {
                    "intent": "sum",
                    "time_period": "last_month",
                    "categories": ["Groceries"],
                    "transaction_type": "expense"
                },
                "expected_sql_contains": ["SUM", "groceries", "expense", "last month date range"],
                "sample_results": [
                    {"amount": -45.50, "payee": "Tesco", "category": "Groceries", "date": "2024-01-15"},
                    {"amount": -32.20, "payee": "Tesco", "category": "Groceries", "date": "2024-01-22"}
                ],
                "expected_summary_contains": ["£77.70", "groceries", "2 transactions"]
            },
            {
                "query": "Show my biggest expense this year",
                "expected_analysis": {
                    "intent": "top",
                    "time_period": "this_year",
                    "transaction_type": "expense"
                },
                "expected_sql_contains": ["ORDER BY", "DESC", "LIMIT", "expense", "this year"],
                "sample_results": [
                    {"amount": -1200.00, "payee": "British Gas", "category": "Bills", "date": "2024-03-01"}
                ],
                "expected_summary_contains": ["£1200.00", "British Gas", "largest"]
            },
            {
                "query": "Count Netflix transactions",
                "expected_analysis": {
                    "intent": "count",
                    "payees": ["Netflix"]
                },
                "expected_sql_contains": ["COUNT", "Netflix", "payee"],
                "sample_results": [
                    {"amount": -9.99, "payee": "Netflix", "category": "Entertainment", "date": "2024-01-01"},
                    {"amount": -9.99, "payee": "Netflix", "category": "Entertainment", "date": "2024-02-01"},
                    {"amount": -9.99, "payee": "Netflix", "category": "Entertainment", "date": "2024-03-01"}
                ],
                "expected_summary_contains": ["3 transactions", "Netflix"]
            },
            {
                "query": "Average restaurant spending",
                "expected_analysis": {
                    "intent": "average",
                    "categories": ["Restaurants"]
                },
                "expected_sql_contains": ["AVG", "restaurant", "category"],
                "sample_results": [
                    {"amount": -25.50, "payee": "Local Cafe", "category": "Restaurants", "date": "2024-01-10"},
                    {"amount": -45.00, "payee": "Local Cafe", "category": "Restaurants", "date": "2024-01-20"}
                ],
                "expected_summary_contains": ["£35.25", "average", "restaurant"]
            },
            {
                "query": "Show all transport expenses",
                "expected_analysis": {
                    "intent": "search",
                    "categories": ["Transport"],
                    "transaction_type": "expense"
                },
                "expected_sql_contains": ["transport", "expense", "category"],
                "sample_results": [
                    {"amount": -12.50, "payee": "Uber", "category": "Transport", "date": "2024-01-05"},
                    {"amount": -8.30, "payee": "Uber", "category": "Transport", "date": "2024-01-12"}
                ],
                "expected_summary_contains": ["2 transactions", "£20.80", "transport"]
            },
            {
                "query": "What did I spend at Tesco today?",
                "expected_analysis": {
                    "intent": "sum",
                    "time_period": "today",
                    "payees": ["Tesco"]
                },
                "expected_sql_contains": ["SUM", "Tesco", "today", "payee"],
                "sample_results": [
                    {"amount": -34.67, "payee": "Tesco", "category": "Groceries", "date": "2024-01-01"}
                ],
                "expected_summary_contains": ["£34.67", "Tesco", "today"]
            },
            {
                "query": "Holiday project expenses",
                "expected_analysis": {
                    "intent": "search",
                    "projects": ["Holiday"]
                },
                "expected_sql_contains": ["project", "Holiday"],
                "sample_results": [
                    {"amount": -450.00, "payee": "Airline", "project": "Holiday", "date": "2024-02-01"},
                    {"amount": -120.00, "payee": "Hotel", "project": "Holiday", "date": "2024-02-02"}
                ],
                "expected_summary_contains": ["£570.00", "Holiday", "2 transactions"]
            },
            {
                "query": "Total income this month",
                "expected_analysis": {
                    "intent": "sum",
                    "time_period": "this_month",
                    "transaction_type": "income"
                },
                "expected_sql_contains": ["SUM", "income", "this month"],
                "sample_results": [
                    {"amount": 2500.00, "payee": "Employer", "type": "income", "date": "2024-01-01"}
                ],
                "expected_summary_contains": ["£2500.00", "income"]
            }
        ]

    def generate_test_set(self, num_additional_cases: int = 20) -> List[Dict]:
        """Generate comprehensive test dataset"""
        test_data = []
        
        # Add predefined test cases
        for i, case in enumerate(self.test_cases):
            test_data.append({
                "id": f"test_{i:03d}",
                "query": case["query"],
                "expected_analysis": case["expected_analysis"],
                "expected_sql_contains": case["expected_sql_contains"],
                "sample_results": case["sample_results"],
                "expected_summary_contains": case["expected_summary_contains"],
                "difficulty": "standard"
            })
        
        # Generate additional random test cases
        for i in range(num_additional_cases):
            case = self._generate_random_test_case(i + len(self.test_cases))
            test_data.append(case)
        
        return test_data
    
    def _generate_random_test_case(self, case_id: int) -> Dict:
        """Generate a random test case"""
        intent = random.choice(["search", "sum", "count", "average", "top"])
        category = random.choice(self.categories)
        payee = random.choice(self.payees)
        time_period = random.choice(["today", "this_month", "last_month"])
        
        if intent == "sum":
            query = f"How much did I spend on {category.lower()} {time_period.replace('_', ' ')}?"
            expected_analysis = {
                "intent": "sum",
                "time_period": time_period,
                "categories": [category],
                "transaction_type": "expense"
            }
            expected_sql = ["SUM", category.lower(), "expense"]
            sample_amount = round(random.uniform(20, 200), 2)
            expected_summary = [f"£{sample_amount}", category.lower()]
            
        elif intent == "count":
            query = f"How many {payee} transactions?"
            expected_analysis = {
                "intent": "count",
                "payees": [payee]
            }
            expected_sql = ["COUNT", payee]
            count = random.randint(2, 8)
            expected_summary = [f"{count} transactions", payee]
            
        elif intent == "top":
            query = f"Show my biggest {category.lower()} expense"
            expected_analysis = {
                "intent": "top",
                "categories": [category],
                "transaction_type": "expense"
            }
            expected_sql = ["ORDER BY", "DESC", "LIMIT", category.lower()]
            amount = round(random.uniform(50, 500), 2)
            expected_summary = [f"£{amount}", "largest", category.lower()]
            
        elif intent == "average":
            query = f"Average {category.lower()} spending"
            expected_analysis = {
                "intent": "average",
                "categories": [category]
            }
            expected_sql = ["AVG", category.lower()]
            avg_amount = round(random.uniform(10, 100), 2)
            expected_summary = [f"£{avg_amount}", "average", category.lower()]
            
        else:  # search
            query = f"Show all {category.lower()} transactions"
            expected_analysis = {
                "intent": "search",
                "categories": [category]
            }
            expected_sql = [category.lower(), "category"]
            total = round(random.uniform(50, 300), 2)
            count = random.randint(3, 10)
            expected_summary = [f"{count} transactions", f"£{total}"]
        
        # Generate sample results
        sample_results = []
        for _ in range(random.randint(1, 3)):
            sample_results.append({
                "amount": -round(random.uniform(5, 100), 2),
                "payee": random.choice([payee] + self.payees[:2]),
                "category": category,
                "date": "2024-01-15"
            })
        
        return {
            "id": f"test_{case_id:03d}",
            "query": query,
            "expected_analysis": expected_analysis,
            "expected_sql_contains": expected_sql,
            "sample_results": sample_results,
            "expected_summary_contains": expected_summary,
            "difficulty": "generated"
        }
    
    def save_test_data(self, test_data: List[Dict], output_path: str):
        """Save test data to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"Generated {len(test_data)} test cases")
        print(f"Test data saved to: {output_path}")
        
        # Show distribution
        difficulties = {}
        intents = {}
        for case in test_data:
            diff = case.get('difficulty', 'unknown')
            difficulties[diff] = difficulties.get(diff, 0) + 1
            intent = case.get('expected_analysis', {}).get('intent', 'unknown')
            intents[intent] = intents.get(intent, 0) + 1
        
        print(f"Difficulty distribution: {difficulties}")
        print(f"Intent distribution: {intents}")

def main():
    parser = argparse.ArgumentParser(description='Generate test data for MoneyTracker AI evaluation')
    parser.add_argument('--num-additional', type=int, default=20,
                       help='Number of additional random test cases to generate')
    parser.add_argument('--output', type=str, default='test_data.json',
                       help='Output file path')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    # Set random seed
    random.seed(args.seed)
    
    print(f"Generating test data with {args.num_additional} additional cases...")
    
    # Generate test data
    generator = TestDataGenerator()
    test_data = generator.generate_test_set(args.num_additional)
    
    # Save test data
    generator.save_test_data(test_data, args.output)
    
    # Show sample test case
    print(f"\n--- Sample Test Case ---")
    sample = test_data[0]
    print(f"Query: {sample['query']}")
    print(f"Expected intent: {sample['expected_analysis']['intent']}")
    print(f"Expected SQL contains: {sample['expected_sql_contains'][:3]}")
    print(f"Expected summary contains: {sample['expected_summary_contains'][:2]}")

if __name__ == "__main__":
    main()