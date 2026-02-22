import os
import json
import requests
import datetime
from google.oauth2 import service_account
import google.auth.transport.requests

class AIService:
    def __init__(self):
        self.log_file = "gemini_api.log"
        self._last_error = None
        
        # Service Account Configuration
        self.sa_key_name = "insightdb-488114-05559aae354e.json"
        self.credentials = None
        self.project_id = "insightdb-488114"
        self.location = "us-central1"
        
        # Determine absolute path for the service account key
        sa_path = None
        possible_paths = [
            os.path.join(os.getcwd(), self.sa_key_name),
            os.path.join(os.path.dirname(__file__), self.sa_key_name),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), self.sa_key_name),
            f"C:\\Users\\acer\\Desktop\\hackfest-2.0\\{self.sa_key_name}"
        ]
        
        for p in possible_paths:
            if os.path.exists(p):
                sa_path = p
                self._log(f"Found Service Account key at: {p}")
                break
        
        if sa_path:
            try:
                # Strictly use 'https://www.googleapis.com/auth/cloud-platform' scope as requested
                self.credentials = service_account.Credentials.from_service_account_file(
                    sa_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.project_id = self.credentials.project_id
                self._log(f"Service Account Loaded. Project: {self.project_id}")
            except Exception as e:
                self._log(f"Service Account Auth Error: {e}")
                self._last_error = f"Auth Init Error: {e}"
        else:
            self._log("CRITICAL: Service Account JSON not found.")
            self._last_error = "Service Account JSON not found."

    def _log(self, message):
        with open(self.log_file, "a") as f:
            f.write(f"[{datetime.datetime.now()}] {message}\n")

    def _get_auth_headers(self):
        """Generates headers strictly using Service Account OAuth2 token."""
        if not self.credentials:
            self._log("No credentials available for OAuth2.")
            return None

        try:
            if not self.credentials.valid:
                self._log("Refreshing OAuth2 token...")
                auth_request = google.auth.transport.requests.Request()
                self.credentials.refresh(auth_request)
            
            # Attach it as Authorization: Bearer <token>
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.credentials.token}"
            }
        except Exception as e:
            err = f"Token Refresh Error: {e}"
            self._log(err)
            self._last_error = err
            return None

    def _call_gemini_rest(self, prompt, is_json=False):
        """Strict Vertex AI REST caller using Service Account OAuth2."""
        headers = self._get_auth_headers()
        if not headers: 
            return None
        
        model_name = "gemini-2.5-flash"
        
        # Vertex AI Endpoint
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{model_name}:generateContent"

        gen_config = {
            "temperature": 0.3,
            "maxOutputTokens": 4096,
        }
        if is_json:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": gen_config
        }

        try:
            self._log("Calling AI core via Vertex AI OAuth2...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                self._log("Success")
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                err_msg = f"AI Error {response.status_code}: {response.text}"
                self._last_error = err_msg
                self._log(err_msg)
                
                if "API_KEY_SERVICE_BLOCKED" in response.text:
                    self._last_error = "Vertex AI API blocked. Ensure API is enabled and billing is active."
                elif "429" in response.text:
                    self._last_error = "Quota Exceeded on Vertex AI."
                    
        except Exception as e:
            self._last_error = f"Request Exception: {e}"
            self._log(self._last_error)
        
        return None

    def chat(self, question, context):
        """Answers a user question based on the provided context."""
        overview = context.get('overview', {})
        schema = context.get('schema', {})
        
        prompt = f"""
        You are the InsightDB AI Assistant. Your goal is to help the user understand their data.
        
        PROJECT CONTEXT:
        Title: {overview.get('title', 'Data Intelligence Project')}
        Description: {overview.get('description', 'Analyzing relational datasets.')}
        Key Entities: {', '.join(overview.get('key_entities', []))}
        
        DATA ARCHITECTURE:
        Tables and Columns: {json.dumps(schema, indent=2)}
        
        USER QUESTION: "{question}"
        
        RESPONSE GUIDELINES:
        - Be professional, helpful, and concise.
        - Use the specific business context provided (e.g., if it's e-commerce, talk about orders, customers, etc.).
        - DO NOT use markdown bold (****) or other markdown formatting.
        - If you want to EMPHASIZE a word or phrase, place exactly TWO asterisks on each side: **Example**.
        - Example: "The **customer_id** is the primary key."
        - Cite metrics or column names if relevant to the question.
        - If the question is about data you don't have, say so politely.
        """
        text = self._call_gemini_rest(prompt, is_json=False)
        if text:
            return text
        
        # If we failed, check if it was a quota issue
        if self._last_error and "429" in self._last_error:
            return "AI core is currently rate-limited (Quota Exceeded). Please wait 60 seconds and try again."
        
        return f"I'm having trouble connecting to my AI core right now. (Status: {self._last_error[:100] if self._last_error else 'Unknown'})"

    def generate_project_overview(self, schemas):
        """Generates a dynamic project background with rich business context."""
        total_rows = sum(s.get("row_count", 0) for s in schemas.values())
        
        # Prepare a token-efficient context (names and column lists only)
        lite_context = []
        for name, info in schemas.items():
            cols = [c['name'] for c in info.get('columns', [])]
            lite_context.append({"table": name, "columns": cols})

        fallback = {
            "title": "InsightDB Intelligence",
            "description": f"AI Documentation Status: {self._last_error[:100] if self._last_error else 'Ready'}",
            "context": "Context extraction skipped due to service limitation.",
            "value": ["Enhanced data transparency", "Identification of relational risks", "Business impact classification"],
            "key_entities": [name.replace("olist_", "").replace("_dataset", "").capitalize() for name in schemas.keys()][:5]
        }

        prompt = f"""
        You are a highly intelligent data architect. Analyze this schema overview and create a professional project documentation JSON.
        
        Context (Table names and columns):
        {json.dumps(lite_context, indent=2)}
        Total Records: {total_rows}

        The JSON must have:
        - title: A specific, non-generic title (e.g., "E-commerce Operations Audit", "Global Logistics Intelligence").
        - description: 2 concise sentences explaining the goal of auditing this specific dataset.
        - context: 2 sentences explaining exactly what this dataset represents (e.g., "This dataset captures the full lifecycle of orders, from customer acquisition to delivery fulfillment").
        - value: An array of 3 specific bullet points describing why this data is valuable for a business.
        - key_entities: An array of the 3-5 most important business entities identified in the data.

        Be smart and specific based on column names. Avoid vague phrases. Ensure the response is valid JSON.
        """

        text = self._call_gemini_rest(prompt, is_json=True)
        if text:
            try:
                clean_text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
            except Exception as e:
                self._log(f"Project Overview Parse Error: {e}")
        
        return fallback

    def generate_full_documentation(self, schemas):
        """Generates a comprehensive long-form documentation report."""
        total_rows = sum(s.get("row_count", 0) for s in schemas.values())
        
        # Context extraction
        lite_context = []
        for name, info in schemas.items():
            cols = [c['name'] for c in info.get('columns', [])]
            lite_context.append({"table": name, "columns": cols})

        prompt = f"""
        You are a Senior Data Architect and Business Consultant. I need a comprehensive Documentation Report for this dataset.
        
        Context (Table names and columns):
        {json.dumps(lite_context, indent=2)}
        Total Records: {total_rows}

        The report MUST be a JSON object with these keys:
        - title: A professional, specific title.
        - executive_summary: A high-level overview of what the dataset represents and its significance (1 paragraph).
        - architecture_overview: How the tables logically relate to each other in a business workflow (1-2 paragraphs).
        - key_entities: Array of objects with {{"name": "Entity", "description": "What this represents in the system"}}.
        - business_utility: 3-5 specific ways a company can use this data for growth or efficiency.
        - data_quality_narrative: An assessment of the dataset based on the structure provided.

        Guidelines:
        - Be specific. If you see customer_id and order_id, talk about the E-commerce lifecycle.
        - Be professional and insightful.
        - Ensure the response is valid JSON.
        """

        text = self._call_gemini_rest(prompt, is_json=True)
        if text:
            try:
                clean_text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
            except Exception as e:
                self._log(f"Full Documentation Parse Error: {e}")
        
        # Minimal Fallback
        return {
            "title": "Dataset Documentation Report",
            "executive_summary": f"Generation Status: {self._last_error[:150] if self._last_error else 'Analysis Pending'}",
            "architecture_overview": "Relational structure analysis was interrupted by a service limit.",
            "key_entities": [],
            "business_utility": ["Check API Key Quota", "Verify Internet Connection", "Refresh after 60 seconds"],
            "data_quality_narrative": "Detailed assessment unavailable at this time."
        }

    def generate_validation_policy(self, schemas):
        """Generates a dynamic validation policy based on schema intent."""
        lite_context = []
        for name, info in schemas.items():
            cols = [{"name": c['name'], "type": c['type']} for c in info.get('columns', [])]
            lite_context.append({"table": name, "columns": cols})

        prompt = f"""
        You are a Data Quality Architect. Analyze the following schema and generate a JSON 'Validation Policy'.
        
        Context:
        {json.dumps(lite_context, indent=2)}

        For each table and column, determine:
        1. is_unsigned: Should this number always be >= 0? (e.g., price, quantity, age). Set FALSE for coords, offsets, temperatures.
        2. range: Min/Max if logically deducible (e.g., latitude: [-90, 90], month: [1, 12]).
        3. regex: Simple pattern if applicable (e.g., zip codes, emails).
        4. sequence_rules: Array of rules like "{{"before": "order_purchase_timestamp", "after": "order_delivered_customer_date"}}" if tables relate.

        Output ONLY valid JSON in this format:
        {{
          "table_name": {{
            "column_name": {{
               "is_unsigned": true,
               "range": [min, max],
               "regex": "...",
               "sequence_rules": [...]
            }}
          }}
        }}

        Be smart. If a column name implies a count or price, it is UNSIGNED.
        """

        text = self._call_gemini_rest(prompt, is_json=True)
        if text:
            try:
                clean_text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
            except Exception as e:
                self._log(f"Validation Policy Parse Error: {e}")
        
        return {}

    def reason_outliers(self, table_name, column_name, row_data, value):
        """Provides AI reasoning for a specific outlier value."""
        prompt = f"""
        Explain why this value might be an outlier or if it might be valid based on context.
        Table: {table_name}
        Column: {column_name}
        Value: {value}
        Row Context: {json.dumps(row_data, indent=2)}

        Provide a 1-sentence logical explanation.
        """
        text = self._call_gemini_rest(prompt, is_json=False)
        return text if text else "Outlier detected via statistical Z-score."
