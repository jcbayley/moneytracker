import json
import os
from datetime import datetime, timedelta
from ..database import Database

# Simple CPU setup for transformers
os.environ['CUDA_VISIBLE_DEVICES'] = ''


class AIQueryService:
    """Service for processing AI queries about transactions."""
    
    def __init__(self):
        self.model_name = "Qwen/Qwen2.5-0.5B-Instruct"
        self.model_dir = os.path.expanduser("~/.local/share/MoneyTracker/models")
        self.model_path = os.path.join(self.model_dir, "qwen2.5-0.5b-instruct")
        self.model = None
        self.sampling_params = None
        self._db_context_cache = None  # Cache for database context
        
        os.makedirs(self.model_dir, exist_ok=True)
        self._load_model()
    
    def _load_model(self):
        """Load the AI model if available."""
        if not os.path.exists(self.model_path):
            print(f"AI model not found. Download required.")
            return
            
        try:
            print("Loading AI model with transformers (CPU)...")
            
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            import torch
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float32,
                device_map="cpu",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            # Create text generation pipeline (no device arg - model already on device)
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                top_p=0.9
            )
            
            print("AI model loaded successfully with transformers")
            
        except Exception as e:
            print(f"Transformers loading failed: {e}")
            self.model = None
    
    def _call_llm(self, prompt):
        """Call the AI model."""
        if self.model is None:
            raise Exception("AI model not loaded. Please download the model first.")
        
        try:
            # Use the pipeline for text generation
            result = self.pipeline(
                prompt,
                max_new_tokens=512,
                pad_token_id=self.tokenizer.eos_token_id,
                return_full_text=False  # Only return generated text
            )
            
            # Extract generated text
            if result and len(result) > 0 and 'generated_text' in result[0]:
                return result[0]['generated_text'].strip()
            return ""
            
        except Exception as e:
            print(f"Model generation failed: {e}")
            raise Exception(f"AI model call failed: {e}")
    
    def process_query(self, user_query):
        """Process user query and return results."""
        analysis = self._analyze_query(user_query)
        transactions = self._search_transactions(analysis)
        summary = self._generate_summary(user_query, analysis, transactions)
        
        # Include query information for UI display
        query_info = getattr(self, 'last_query_info', {})
        
        return {
            'query': user_query,
            'summary': summary,
            'transactions': [dict(t) for t in transactions] if transactions else [],
            'analysis': analysis,
            'database_query': query_info.get('formatted_sql', ''),
            'query_params': query_info.get('params', [])
        }
    
    def _analyze_query(self, query):
        """Analyze user query using AI with database context."""
        # Get available categories and payees from database
        db_context = self._get_database_context()
        
        prompt = f"""Extract financial query parameters as JSON:

Query: "{query}"

Available data in database:
Categories: {', '.join(db_context['categories'][:20])}
Payees: {', '.join(db_context['payees'][:20])}
Projects: {', '.join(db_context['projects'][:10])}

INTENT MAPPING EXAMPLES:
- "largest/biggest/most expensive" → intent: "top" (will ORDER BY amount DESC)
- "smallest/cheapest/lowest" → intent: "top" (will ORDER BY amount DESC, but show smallest)
- "total/sum/how much spent" → intent: "sum" (will calculate total)
- "average/mean" → intent: "average" (will calculate average)
- "how many/count" → intent: "count" (will count transactions)
- "show me/find/list" → intent: "search" (will show transactions)

TIME PERIOD DETECTION:
- Look for: today, yesterday, last week, this month, last month, this year, last year
- "past week" = "last_week", "current month" = "this_month"

Return JSON with:
- intent: "search", "sum", "top", "average", or "count"
- time_period: exact match from list above or null
- categories: EXACT category names from available list (empty if not mentioned)
- payees: EXACT payee names from available list (empty if not mentioned)  
- projects: EXACT project names from available list (empty if not mentioned)
- amount_filter: {{"type": "greater"/"less", "amount": number}} or null
- transaction_type: "income", "expense", "transfer" or null (detect from context)

CRITICAL: For "largest/biggest/top" queries, ALWAYS use intent: "top" - this ensures proper sorting by amount!

JSON only:"""
        
        output = self._call_llm(prompt)
        
        # Extract and parse JSON
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(output[json_start:json_end])
            except json.JSONDecodeError:
                pass
                
        # Fallback default
        return {
            'intent': 'search', 'time_period': None, 'categories': [],
            'payees': [], 'projects': [], 'amount_filter': None, 'transaction_type': None
        }
    
    def _get_database_context(self):
        """Get available categories, payees, and projects from database (with caching)."""
        if self._db_context_cache is not None:
            return self._db_context_cache
            
        with Database.get_db() as db:
            # Get categories from dedicated table
            categories_result = db.execute("""
                SELECT name FROM categories ORDER BY name
            """).fetchall()
            
            # Get payees from dedicated table
            payees_result = db.execute("""
                SELECT name FROM payees ORDER BY name
            """).fetchall()
            
            # Get projects from dedicated table
            projects_result = db.execute("""
                SELECT name FROM projects ORDER BY name
            """).fetchall()
            
            self._db_context_cache = {
                'categories': [row['name'] for row in categories_result],
                'payees': [row['name'] for row in payees_result],
                'projects': [row['name'] for row in projects_result]
            }
            
            return self._db_context_cache
    
    def _search_transactions(self, analysis):
        """Search transactions based on analysis."""
        with Database.get_db() as db:
            query = "SELECT t.*, a.name as account_name FROM transactions t JOIN accounts a ON t.account_id = a.id WHERE 1=1"
            params = []
            
            # Time filter
            if analysis.get('time_period'):
                start_date, end_date = self._get_date_range(analysis['time_period'])
                if start_date:
                    query += " AND t.date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND t.date <= ?"
                    params.append(end_date)
            
            # Type filter
            if analysis.get('transaction_type'):
                query += " AND t.type = ?"
                params.append(analysis['transaction_type'])
            
            # Category filter
            if analysis.get('categories'):
                conditions = [f"t.category LIKE ?" for _ in analysis['categories']]
                query += f" AND ({' OR '.join(conditions)})"
                params.extend([f"%{cat}%" for cat in analysis['categories']])
            
            # Payee filter
            if analysis.get('payees'):
                conditions = [f"t.payee LIKE ?" for _ in analysis['payees']]
                query += f" AND ({' OR '.join(conditions)})"
                params.extend([f"%{payee}%" for payee in analysis['payees']])
            
            # Project filter
            if analysis.get('projects'):
                conditions = [f"t.project LIKE ?" for _ in analysis['projects']]
                query += f" AND ({' OR '.join(conditions)})"
                params.extend([f"%{project}%" for project in analysis['projects']])
            
            # Amount filter
            if analysis.get('amount_filter'):
                op = ">" if analysis['amount_filter']['type'] == 'greater' else "<"
                query += f" AND ABS(t.amount) {op} ?"
                params.append(analysis['amount_filter']['amount'])
            
            # Ordering based on intent
            if analysis.get('intent') == 'top':
                query += " ORDER BY ABS(t.amount) DESC LIMIT 1000"
            elif analysis.get('intent') == 'sum':
                query += " ORDER BY ABS(t.amount) DESC LIMIT 1000"  # More results for sum calculations
            elif analysis.get('intent') == 'average':
                query += " ORDER BY t.date DESC LIMIT 1000"  # More results for average calculations
            elif analysis.get('intent') == 'count':
                query += " ORDER BY t.date DESC LIMIT 1000"  # Even more for counting
            else:
                query += " ORDER BY t.date DESC LIMIT 1000"  # Default search
            
            # Store query info for display
            self.last_query_info = {
                'sql': query,
                'params': params,
                'formatted_sql': self._format_query_for_display(query, params)
            }
            
            return db.execute(query, params).fetchall()
    
    def _format_query_for_display(self, query, params):
        """Format SQL query for user-friendly display."""
        # Replace parameter placeholders with actual values for display
        display_query = query
        for param in params:
            if isinstance(param, str):
                display_query = display_query.replace('?', f"'{param}'", 1)
            else:
                display_query = display_query.replace('?', str(param), 1)
        
        # Format for better readability
        display_query = display_query.replace(' AND ', '\n  AND ')
        display_query = display_query.replace(' FROM ', '\n  FROM ')
        display_query = display_query.replace(' JOIN ', '\n  JOIN ')
        display_query = display_query.replace(' WHERE ', '\n  WHERE ')
        display_query = display_query.replace(' ORDER BY ', '\n  ORDER BY ')
        
        return display_query
    
    def _get_date_range(self, period):
        """Convert period string to date range."""
        now = datetime.now()
        
        ranges = {
            'today': (now, now),
            'yesterday': (now - timedelta(days=1), now - timedelta(days=1)),
            'last_week': (now - timedelta(days=7), now),
            'this_month': (now.replace(day=1), now),
            'last_month': self._get_last_month_range(now),
            'this_year': (now.replace(month=1, day=1), now),
            'last_year': (now.replace(year=now.year-1, month=1, day=1), now.replace(year=now.year-1, month=12, day=31))
        }
        
        if period in ranges:
            start, end = ranges[period]
            return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
        return None, None
    
    def _get_last_month_range(self, now):
        """Get last month date range."""
        first_this_month = now.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    
    def _generate_summary(self, user_query, analysis, transactions):
        """Generate AI-powered summary of results."""
        if not transactions:
            return "No transactions found matching your query."
        
        # Let AI generate the summary based on the original query and results
        count = len(transactions)
        total = sum(abs(t['amount']) for t in transactions)
        
        # Get top few transactions for context
        top_transactions = sorted(transactions, key=lambda x: abs(x['amount']), reverse=True)[:3]
        top_tx_context = []
        for tx in top_transactions:
            top_tx_context.append(f"£{abs(tx['amount']):.2f} to {tx['payee'] or 'Unknown'} on {tx['date']}")
        
        summary_prompt = f"""Analyze this financial query step by step, then provide ONE final response:

USER QUESTION: "{user_query}"
QUERY ANALYSIS: {analysis}
ALL TRANSACTIONS: {'; '.join(top_tx_context)}

you should format your response as json with 
 - REASONING: [Complete analysis - what is the user asking for, what does the data show, what's the best answer]
 - RESPONSE: [Final short helpful answer with relevant numbers - this will be shown to the user]"""
        
        try:
            ai_output = self._call_llm(summary_prompt)
            if ai_output and ai_output.strip():
                # Try to parse as JSON and extract RESPONSE
                try:
                    # Find JSON in the output
                    json_start = ai_output.find('{')
                    json_end = ai_output.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = ai_output[json_start:json_end]
                        parsed_json = json.loads(json_str)
                        
                        # Extract RESPONSE field
                        if 'RESPONSE' in parsed_json:
                            return parsed_json['RESPONSE'].strip()
                        elif 'response' in parsed_json:
                            return parsed_json['response'].strip()
                    
                    # If JSON parsing fails, try fallback extraction
                    if 'RESPONSE' in ai_output:
                        response_start = ai_output.find('RESPONSE')
                        response_part = ai_output[response_start:].split('\n')[0]
                        return response_part.replace('RESPONSE:', '').replace('"', '').strip()
                    
                except json.JSONDecodeError:
                    # JSON parsing failed, try to extract manually
                    if '"RESPONSE"' in ai_output:
                        response_start = ai_output.find('"RESPONSE"')
                        response_section = ai_output[response_start:]
                        # Find the value after "RESPONSE": "
                        colon_pos = response_section.find(':')
                        if colon_pos > 0:
                            value_start = response_section.find('"', colon_pos) + 1
                            value_end = response_section.find('"', value_start)
                            if value_start > 0 and value_end > value_start:
                                return response_section[value_start:value_end].strip()
                
                # Final fallback
                return ai_output.strip()
        except Exception as e:
            print(f"AI summary generation failed: {e}")
        
        # Fallback to simple summary
        return f"Found {count} transactions totaling £{total:.2f}."
    
    def check_model_status(self):
        """Check model download status."""
        exists = os.path.exists(self.model_path) and os.path.isdir(self.model_path)
        loaded = self.model is not None
        
        if exists:
            files = os.listdir(self.model_path)
            has_config = any('config.json' in f for f in files)
            has_model = any(f.endswith(('.bin', '.safetensors')) for f in files)
            ready = has_config and has_model and loaded
        else:
            ready = False
        
        return {
            'downloaded': ready,
            'model_name': self.model_name,
            'model_path': self.model_path
        }
    
    def download_model(self, progress_callback=None):
        """Download the AI model."""
        try:
            if progress_callback:
                progress_callback.update({'status': 'downloading', 'progress': 10, 'message': 'Starting download...'})
            
            from huggingface_hub import snapshot_download
            
            snapshot_download(
                repo_id=self.model_name,
                local_dir=self.model_path,
                local_dir_use_symlinks=False
            )
            
            if progress_callback:
                progress_callback.update({'progress': 90, 'message': 'Verifying files...'})
            
            # Verify download
            files = os.listdir(self.model_path)
            has_config = any('config.json' in f for f in files)
            has_model = any(f.endswith(('.bin', '.safetensors')) for f in files)
            
            if has_config and has_model:
                if progress_callback:
                    progress_callback.update({'progress': 100, 'status': 'completed', 'message': 'Download complete!'})
                
                self._load_model()
                return True
            else:
                raise Exception("Download verification failed")
                
        except Exception as e:
            if progress_callback:
                progress_callback.update({'status': 'error', 'message': f'Download failed: {e}'})
            return False