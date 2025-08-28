#!/usr/bin/env python3
"""
Model Evaluation Script for MoneyTracker AI Fine-tuning

Compares fine-tuned model performance against the original base model
on SQL generation and result summarization tasks.
"""

import torch
import json
import argparse
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from peft import PeftModel
import difflib
from collections import Counter

@dataclass
class EvaluationResult:
    """Results from evaluating a single test case"""
    test_id: str
    query: str
    base_model_output: str
    finetuned_output: str
    base_score: float
    finetuned_score: float
    improvement: float
    analysis_accuracy: Dict[str, float]
    sql_accuracy: float
    summary_accuracy: float

class ModelEvaluator:
    def __init__(self, base_model_name: str, finetuned_model_path: str = None):
        self.base_model_name = base_model_name
        self.finetuned_model_path = finetuned_model_path
        
        print(f"Loading base model: {base_model_name}")
        self.base_tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name, 
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True
        )
        
        # Add padding token if missing
        if self.base_tokenizer.pad_token is None:
            self.base_tokenizer.pad_token = self.base_tokenizer.eos_token
        
        # Setup base model pipeline
        self.base_pipeline = pipeline(
            "text-generation",
            model=self.base_model,
            tokenizer=self.base_tokenizer,
            max_new_tokens=256,
            temperature=0.1,  # Low temperature for consistent results
            do_sample=True,
            return_full_text=False
        )
        
        # Load fine-tuned model if provided
        if finetuned_model_path:
            print(f"Loading fine-tuned model from: {finetuned_model_path}")
            self.finetuned_model = PeftModel.from_pretrained(self.base_model, finetuned_model_path)
            self.finetuned_pipeline = pipeline(
                "text-generation",
                model=self.finetuned_model,
                tokenizer=self.base_tokenizer,  # Same tokenizer
                max_new_tokens=256,
                temperature=0.1,
                do_sample=True,
                return_full_text=False
            )
        else:
            self.finetuned_model = None
            self.finetuned_pipeline = None
    
    def generate_response(self, prompt: str, use_finetuned: bool = False) -> str:
        """Generate response from model"""
        pipeline_to_use = self.finetuned_pipeline if (use_finetuned and self.finetuned_pipeline) else self.base_pipeline
        
        try:
            result = pipeline_to_use(prompt)
            if result and len(result) > 0 and 'generated_text' in result[0]:
                return result[0]['generated_text'].strip()
            return ""
        except Exception as e:
            print(f"Generation error: {e}")
            return ""
    
    def create_evaluation_prompt(self, test_case: Dict) -> str:
        """Create evaluation prompt matching training format"""
        return f"User Query: {test_case['query']}\n\nAnalysis:"
    
    def extract_analysis_from_response(self, response: str) -> Dict:
        """Extract JSON analysis from model response"""
        try:
            # Look for JSON-like structure
            json_match = re.search(r'\{[^}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Clean up common issues
                json_str = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', json_str)  # Quote keys
                json_str = re.sub(r':\s*([^",\[\]{}]+)([,}])', r': "\1"\2', json_str)  # Quote values
                return json.loads(json_str)
        except:
            pass
        
        # Fallback: extract intent manually
        intent_match = re.search(r'intent["\']?\s*:\s*["\']?(\w+)["\']?', response, re.IGNORECASE)
        intent = intent_match.group(1) if intent_match else "unknown"
        
        return {"intent": intent}
    
    def score_analysis_accuracy(self, predicted: Dict, expected: Dict) -> Dict[str, float]:
        """Score how well the analysis matches expected output"""
        scores = {}
        
        # Intent accuracy (most important)
        predicted_intent = predicted.get('intent', '').lower()
        expected_intent = expected.get('intent', '').lower()
        scores['intent'] = 1.0 if predicted_intent == expected_intent else 0.0
        
        # Categories accuracy
        pred_cats = set([c.lower() for c in predicted.get('categories', [])])
        exp_cats = set([c.lower() for c in expected.get('categories', [])])
        if exp_cats:
            scores['categories'] = len(pred_cats & exp_cats) / len(exp_cats)
        else:
            scores['categories'] = 1.0 if not pred_cats else 0.5
        
        # Payees accuracy
        pred_payees = set([p.lower() for p in predicted.get('payees', [])])
        exp_payees = set([p.lower() for p in expected.get('payees', [])])
        if exp_payees:
            scores['payees'] = len(pred_payees & exp_payees) / len(exp_payees)
        else:
            scores['payees'] = 1.0 if not pred_payees else 0.5
        
        # Time period accuracy
        pred_time = predicted.get('time_period', '').lower()
        exp_time = expected.get('time_period', '').lower()
        scores['time_period'] = 1.0 if pred_time == exp_time else 0.0
        
        # Transaction type accuracy
        pred_type = predicted.get('transaction_type', '').lower()
        exp_type = expected.get('transaction_type', '').lower()
        scores['transaction_type'] = 1.0 if pred_type == exp_type else 0.0
        
        return scores
    
    def score_sql_accuracy(self, response: str, expected_contains: List[str]) -> float:
        """Score SQL generation accuracy based on expected keywords"""
        if not expected_contains:
            return 1.0
        
        response_lower = response.lower()
        matches = 0
        
        for expected in expected_contains:
            expected_lower = expected.lower()
            
            # Check for direct matches or SQL-related terms
            if expected_lower in response_lower:
                matches += 1
            elif expected_lower == "sum" and any(word in response_lower for word in ["sum", "total", "aggregate"]):
                matches += 1
            elif expected_lower == "count" and any(word in response_lower for word in ["count", "number"]):
                matches += 1
            elif "order by" in expected_lower and any(phrase in response_lower for phrase in ["order", "sort", "top", "biggest"]):
                matches += 1
            elif "desc" in expected_lower and any(word in response_lower for word in ["desc", "descending", "largest", "highest"]):
                matches += 1
        
        return matches / len(expected_contains)
    
    def score_summary_accuracy(self, response: str, expected_contains: List[str]) -> float:
        """Score summary accuracy based on expected content"""
        if not expected_contains:
            return 1.0
        
        response_lower = response.lower()
        matches = 0
        
        for expected in expected_contains:
            expected_lower = expected.lower()
            
            # Check for exact matches or close variants
            if expected_lower in response_lower:
                matches += 1
            elif "£" in expected_lower:
                # Check for currency amounts
                amount_match = re.search(r'£(\d+\.?\d*)', expected_lower)
                if amount_match:
                    amount = amount_match.group(1)
                    if amount in response_lower:
                        matches += 1
            elif "transaction" in expected_lower and "transaction" in response_lower:
                matches += 1
        
        return matches / len(expected_contains)
    
    def calculate_overall_score(self, analysis_scores: Dict[str, float], sql_score: float, summary_score: float) -> float:
        """Calculate overall score with weighted components"""
        intent_score = analysis_scores.get('intent', 0.0)
        
        # Weights: Intent is most important, then SQL generation, then summary
        overall_score = (
            intent_score * 0.4 +           # Intent recognition: 40%
            sql_score * 0.35 +             # SQL accuracy: 35%
            summary_score * 0.25           # Summary accuracy: 25%
        )
        
        return overall_score
    
    def evaluate_test_case(self, test_case: Dict) -> EvaluationResult:
        """Evaluate a single test case"""
        prompt = self.create_evaluation_prompt(test_case)
        
        # Generate responses from both models
        base_response = self.generate_response(prompt, use_finetuned=False)
        finetuned_response = self.generate_response(prompt, use_finetuned=True) if self.finetuned_pipeline else ""
        
        # Extract and score analysis
        base_analysis = self.extract_analysis_from_response(base_response)
        finetuned_analysis = self.extract_analysis_from_response(finetuned_response) if finetuned_response else {}
        
        base_analysis_scores = self.score_analysis_accuracy(base_analysis, test_case['expected_analysis'])
        finetuned_analysis_scores = self.score_analysis_accuracy(finetuned_analysis, test_case['expected_analysis']) if finetuned_response else {}
        
        # Score SQL accuracy
        base_sql_score = self.score_sql_accuracy(base_response, test_case['expected_sql_contains'])
        finetuned_sql_score = self.score_sql_accuracy(finetuned_response, test_case['expected_sql_contains']) if finetuned_response else 0.0
        
        # Score summary accuracy
        base_summary_score = self.score_summary_accuracy(base_response, test_case['expected_summary_contains'])
        finetuned_summary_score = self.score_summary_accuracy(finetuned_response, test_case['expected_summary_contains']) if finetuned_response else 0.0
        
        # Calculate overall scores
        base_overall = self.calculate_overall_score(base_analysis_scores, base_sql_score, base_summary_score)
        finetuned_overall = self.calculate_overall_score(finetuned_analysis_scores, finetuned_sql_score, finetuned_summary_score) if finetuned_response else 0.0
        
        return EvaluationResult(
            test_id=test_case['id'],
            query=test_case['query'],
            base_model_output=base_response,
            finetuned_output=finetuned_response,
            base_score=base_overall,
            finetuned_score=finetuned_overall,
            improvement=finetuned_overall - base_overall,
            analysis_accuracy=finetuned_analysis_scores,
            sql_accuracy=finetuned_sql_score,
            summary_accuracy=finetuned_summary_score
        )
    
    def evaluate_all(self, test_data: List[Dict]) -> List[EvaluationResult]:
        """Evaluate all test cases"""
        results = []
        
        print(f"Evaluating {len(test_data)} test cases...")
        
        for i, test_case in enumerate(test_data):
            print(f"Evaluating {i+1}/{len(test_data)}: {test_case['query'][:50]}...")
            result = self.evaluate_test_case(test_case)
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[EvaluationResult]) -> Dict:
        """Generate evaluation report"""
        if not results:
            return {"error": "No results to analyze"}
        
        base_scores = [r.base_score for r in results]
        finetuned_scores = [r.finetuned_score for r in results if r.finetuned_output]
        improvements = [r.improvement for r in results if r.finetuned_output]
        
        report = {
            "summary": {
                "total_test_cases": len(results),
                "base_model_avg_score": sum(base_scores) / len(base_scores),
                "finetuned_model_avg_score": sum(finetuned_scores) / len(finetuned_scores) if finetuned_scores else 0.0,
                "average_improvement": sum(improvements) / len(improvements) if improvements else 0.0,
                "improved_cases": len([i for i in improvements if i > 0]),
                "degraded_cases": len([i for i in improvements if i < 0]),
                "unchanged_cases": len([i for i in improvements if i == 0])
            },
            "detailed_scores": {
                "intent_accuracy": sum([r.analysis_accuracy.get('intent', 0) for r in results]) / len(results),
                "sql_accuracy": sum([r.sql_accuracy for r in results]) / len(results),
                "summary_accuracy": sum([r.summary_accuracy for r in results]) / len(results)
            },
            "best_improvements": sorted([
                {"test_id": r.test_id, "query": r.query, "improvement": r.improvement}
                for r in results if r.improvement > 0
            ], key=lambda x: x['improvement'], reverse=True)[:5],
            "worst_cases": sorted([
                {"test_id": r.test_id, "query": r.query, "improvement": r.improvement}
                for r in results if r.improvement < 0
            ], key=lambda x: x['improvement'])[:5]
        }
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Evaluate fine-tuned model against base model')
    parser.add_argument('--base-model', type=str, default='HuggingFaceTB/SmolLM2-360M-Instruct',
                       help='Base model name')
    parser.add_argument('--finetuned-model', type=str, required=True,
                       help='Path to fine-tuned model (LoRA adapters)')
    parser.add_argument('--test-data', type=str, default='test_data.json',
                       help='Path to test data JSON file')
    parser.add_argument('--output', type=str, default='evaluation_results.json',
                       help='Output file for detailed results')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of test cases to evaluate')
    
    args = parser.parse_args()
    
    # Load test data
    print(f"Loading test data from: {args.test_data}")
    with open(args.test_data, 'r') as f:
        test_data = json.load(f)
    
    if args.limit:
        test_data = test_data[:args.limit]
    
    # Initialize evaluator
    evaluator = ModelEvaluator(args.base_model, args.finetuned_model)
    
    # Run evaluation
    results = evaluator.evaluate_all(test_data)
    
    # Generate report
    report = evaluator.generate_report(results)
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print(f"Total test cases: {report['summary']['total_test_cases']}")
    print(f"Base model average score: {report['summary']['base_model_avg_score']:.3f}")
    print(f"Fine-tuned model average score: {report['summary']['finetuned_model_avg_score']:.3f}")
    print(f"Average improvement: {report['summary']['average_improvement']:.3f}")
    print(f"Cases improved: {report['summary']['improved_cases']}")
    print(f"Cases degraded: {report['summary']['degraded_cases']}")
    
    print(f"\nDetailed Accuracies:")
    print(f"Intent recognition: {report['detailed_scores']['intent_accuracy']:.3f}")
    print(f"SQL generation: {report['detailed_scores']['sql_accuracy']:.3f}")
    print(f"Summary generation: {report['detailed_scores']['summary_accuracy']:.3f}")
    
    # Save detailed results
    detailed_results = {
        "evaluation_report": report,
        "individual_results": [
            {
                "test_id": r.test_id,
                "query": r.query,
                "base_score": r.base_score,
                "finetuned_score": r.finetuned_score,
                "improvement": r.improvement,
                "base_output": r.base_model_output,
                "finetuned_output": r.finetuned_output
            }
            for r in results
        ]
    }
    
    with open(args.output, 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nDetailed results saved to: {args.output}")

if __name__ == "__main__":
    main()