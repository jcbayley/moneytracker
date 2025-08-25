import json
import os
from datetime import datetime, timedelta
from ..database import Database

# Simple CPU setup for transformers
os.environ['CUDA_VISIBLE_DEVICES'] = ''


class AIQueryService:
    """Service for processing AI queries about transactions."""
    
    def __init__(self):
        #self.model_name = "Qwen/Qwen2.5-0.5B-Instruct"
        self.model_name = "Qwen/Qwen2.5-3B"
        self.model_dir = os.path.expanduser("~/.local/share/MoneyTracker/models")
        self.model_path = os.path.join(self.model_dir, "Qwen2.5-3B")
        self.model = None
        self.sampling_params = None
        self._db_context_cache = None  # Cache for database context
        self._config = None  # AI configuration
        
        os.makedirs(self.model_dir, exist_ok=True)
        self._load_config()
        # Only load local model if config is set to local
        if self._config.get('type') == 'local':
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
    
    def _load_config(self):
        """Load AI configuration."""
        try:
            config_path = os.path.expanduser("~/.local/share/MoneyTracker/ai_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self._config = json.load(f)
            else:
                self._config = {'type': 'local'}
        except Exception as e:
            print(f"Failed to load AI config: {e}")
            self._config = {'type': 'local'}

    def _call_llm(self, prompt):
        """Call the AI model (local or API)."""
        if self._config.get('type') == 'api':
            return self._call_api(prompt)
        else:
            return self._call_local_model(prompt)

    def _call_local_model(self, prompt):
        """Call the local AI model."""
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

    def _call_api(self, prompt):
        """Call external API."""
        import requests
        
        url = self._config.get('url', '').strip()
        model = self._config.get('model', '').strip()
        api_key = self._config.get('api_key', '').strip()
        
        if not url or not model:
            raise Exception("API configuration incomplete. Please configure API settings.")
        
        try:
            if 'ollama' in url.lower() or ':11434' in url:
                # Ollama API
                api_url = f"{url.rstrip('/')}/api/generate"
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Lower temp for more consistent results
                        "top_p": 0.9,
                        "num_predict": 100   # Limit output tokens for speed
                    }
                }
                response = requests.post(api_url, json=payload, timeout=120)
                if response.status_code == 200:
                    result = response.json().get('response', '')
                    return result
                else:
                    raise Exception(f"API error: {response.status_code}")
                    
            else:
                raise Exception("Unsupported API type")
                
        except requests.exceptions.Timeout:
            raise Exception("API request timeout")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to API")
        except Exception as e:
            raise Exception(f"API call failed: {e}")
    
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
        
        prompt = f"""Parse financial query to JSON for sql search:
Query: "{query}"

Categories: {', '.join(db_context['categories'][:10])}
Payees: {', '.join(db_context['payees'][:10])}

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
}}"""
        
        output = self._call_llm(prompt)
        
        # Extract and parse JSON
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            try:
                result = json.loads(output[json_start:json_end])
                
                # Fallback transaction type detection if LLM missed it
                if not result.get('transaction_type'):
                    query_lower = query.lower()
                    if any(word in query_lower for word in ['expense', 'expenses', 'spent', 'spending', 'paid', 'cost', 'bill', 'purchase']):
                        result['transaction_type'] = 'expense'
                    elif any(word in query_lower for word in ['income', 'earned', 'salary', 'revenue', 'received', 'deposit']):
                        result['transaction_type'] = 'income'
                    elif 'transfer' in query_lower:
                        result['transaction_type'] = 'transfer'
                
                return result
            except json.JSONDecodeError:
                pass
                
        # Fallback default with transaction type detection
        result = {
            'intent': 'search', 'time_period': None, 'custom_date': None, 'categories': [],
            'payees': [], 'projects': [], 'amount_filter': None, 'transaction_type': None
        }
        
        # Fallback transaction type detection
        query_lower = query.lower()
        if any(word in query_lower for word in ['expense', 'expenses', 'spent', 'spending', 'paid', 'cost', 'bill', 'purchase']):
            result['transaction_type'] = 'expense'
        elif any(word in query_lower for word in ['income', 'earned', 'salary', 'revenue', 'received', 'deposit']):
            result['transaction_type'] = 'income'
        elif 'transfer' in query_lower:
            result['transaction_type'] = 'transfer'
            
        return result
    
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
            
            # Custom date filter (flexible dates)
            elif analysis.get('custom_date'):
                start_date, end_date = self._parse_custom_date(analysis['custom_date'])
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
            
            # Category filter (only if explicitly mentioned and not empty)
            if analysis.get('categories') and any(cat.strip() for cat in analysis['categories']):
                conditions = [f"t.category LIKE ?" for cat in analysis['categories'] if cat.strip()]
                if conditions:
                    query += f" AND ({' OR '.join(conditions)})"
                    params.extend([f"%{cat}%" for cat in analysis['categories'] if cat.strip()])
            
            # Payee filter (only if explicitly mentioned and not empty)
            if analysis.get('payees') and any(payee.strip() for payee in analysis['payees']):
                conditions = [f"t.payee LIKE ?" for payee in analysis['payees'] if payee.strip()]
                if conditions:
                    query += f" AND ({' OR '.join(conditions)})"
                    params.extend([f"%{payee}%" for payee in analysis['payees'] if payee.strip()])
            
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
    
    def _parse_custom_date(self, date_str):
        """Parse flexible date strings into date ranges."""
        from datetime import datetime
        import re
        
        date_str = date_str.lower().strip()
        now = datetime.now()
        
        try:
            # YYYY-MM-DD format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                date = datetime.strptime(date_str, '%Y-%m-%d')
                return date.strftime('%Y-%m-%d'), date.strftime('%Y-%m-%d')
            
            # YYYY-MM format
            elif re.match(r'^\d{4}-\d{2}$', date_str):
                year, month = date_str.split('-')
                start = f"{year}-{month}-01"
                # Get last day of month
                if int(month) == 12:
                    end_year, end_month = int(year) + 1, 1
                else:
                    end_year, end_month = int(year), int(month) + 1
                end_date = datetime(end_year, end_month, 1) - timedelta(days=1)
                return start, end_date.strftime('%Y-%m-%d')
            
            # Month names
            elif any(month in date_str for month in ['january', 'february', 'march', 'april', 'may', 'june', 
                                                    'july', 'august', 'september', 'october', 'november', 'december']):
                months = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                         'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
                
                # Extract year if present
                year_match = re.search(r'\b(20\d{2})\b', date_str)
                year = int(year_match.group(1)) if year_match else now.year
                
                # Find month
                for month_name, month_num in months.items():
                    if month_name in date_str:
                        start = f"{year}-{month_num:02d}-01"
                        if month_num == 12:
                            end_year, end_month = year + 1, 1
                        else:
                            end_year, end_month = year, month_num + 1
                        end_date = datetime(end_year, end_month, 1) - timedelta(days=1)
                        return start, end_date.strftime('%Y-%m-%d')
            
        except:
            pass
        
        return None, None
    
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
        
        summary_prompt = f"""Answer user's financial question:
Question: "{user_query}"
Found {count} transactions, total £{total:.2f}
Top amounts: {'; '.join(top_tx_context[:2])}

Provide short direct answer:"""
        
        try:
            ai_output = self._call_llm(summary_prompt)
            if ai_output and ai_output.strip():
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