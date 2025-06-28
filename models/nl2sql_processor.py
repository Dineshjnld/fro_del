"""
Natural Language to SQL Processor using Hugging Face Transformers
"""
import logging
import asyncio
import re
import torch
from typing import Dict, Any, List, Optional
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from config.settings import settings # For USE_GPU and MODELS_DIR

logger = logging.getLogger(__name__)

class NL2SQLProcessor:
    """Convert natural language queries to SQL using a transformer model."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the NL2SQLProcessor.
        Args:
            config: A dictionary containing the configuration.
                    Expected to have 'nl2sql' or 'cctns_schema' for schema details,
                    and 'nl2sql.primary.name' for the model name.
        """
        self.config = config
        # Determine schema source: 'cctns_schema' is preferred from models_config.yml
        # The 'nl2sql' key in models_config.yml is more for model choice.
        schema_config = config.get("cctns_schema", config.get("nl2sql", {}))

        self.database_type = schema_config.get("database_type", "oracle")
        self.schema_tables = schema_config.get("tables", [])
        self.serialized_schema_cache: Optional[str] = None

        # Model Configuration
        model_config = config.get("nl2sql", {}).get("primary", {})
        self.model_name = model_config.get("name", "microsoft/CodeT5-base") # Default if not in config

        # Model generation parameters
        self.max_length = model_config.get("max_length", 512) # Max length for generated SQL
        self.num_beams = model_config.get("num_beams", 4)
        self.temperature = float(model_config.get("temperature", 1.0)) # Ensure float
        self.early_stopping = model_config.get("early_stopping", True)


        self.device = torch.device("cuda" if torch.cuda.is_available() and getattr(settings, 'USE_GPU', False) else "cpu")
        self.tokenizer = None
        self.model = None
        self._load_model()

        logger.info(f"🔍 NL2SQLProcessor initialized for {self.database_type} DB. Using model: {self.model_name} on {self.device}")

    def _load_model(self):
        try:
            logger.info(f"Loading NL2SQL model: {self.model_name}...")
            cache_dir = getattr(settings, 'MODELS_DIR', None)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, cache_dir=cache_dir)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name, cache_dir=cache_dir)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"✅ NL2SQL model '{self.model_name}' loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load NL2SQL model '{self.model_name}': {e}", exc_info=True)
            # Application might still run but NL2SQL will fail.
            # Consider raising an error or setting a flag.

    def _serialize_schema(self) -> str:
        """
        Serializes the database schema into a string format suitable for prompting an NL2SQL model.
        Includes table names, column names, types, and primary/foreign keys.
        Column descriptions are added as comments if available.
        """
        if self.serialized_schema_cache:
            return self.serialized_schema_cache

        if not self.schema_tables:
            logger.warning("Schema definition (tables) is empty. NL2SQL may be ineffective.")
            return ""

        schema_parts = []
        for table in self.schema_tables:
            table_name = table.get("name")
            if not table_name:
                continue

            columns_str_parts = []
            for col_info in table.get("columns", []):
                col_name = col_info.get("name")
                col_type = col_info.get("type", "TEXT")
                col_desc = col_info.get("description")
                col_part = f"{col_name} {col_type}"
                if col_desc:
                    col_part += f" /* {col_desc} */"
                columns_str_parts.append(col_part)
            
            columns_str = ", ".join(columns_str_parts)
            schema_parts.append(f"CREATE TABLE {table_name} ({columns_str});")

            pk = table.get("primary_key")
            if pk:
                schema_parts.append(f"-- PK for {table_name}: {pk}")

            fks = table.get("foreign_keys", [])
            if fks:
                fk_strs = [f"{fk.get('column')} REFERENCES {fk.get('references')}" for fk in fks]
                schema_parts.append(f"-- FKs for {table_name}: {'; '.join(fk_strs)}")

        self.serialized_schema_cache = "\n".join(schema_parts)
        logger.info(f"Serialized schema for NL2SQL model (first 500 chars): {self.serialized_schema_cache[:500]}")
        return self.serialized_schema_cache

    async def generate_sql(self, text: str) -> Dict[str, Any]:
        """
        Generate SQL query from natural language text using the loaded transformer model.
        """
        if not self.model or not self.tokenizer:
            logger.error("NL2SQL model not loaded. Cannot generate SQL.")
            return {"sql": "", "valid": False, "confidence": 0.0, "error": "NL2SQL model not available."}

        try:
            logger.info(f"🔍 Generating SQL for query: \"{text}\"")
            
            serialized_schema = self._serialize_schema()
            if not serialized_schema:
                 logger.warning("Schema is not available for NL2SQL generation.")
                 # Potentially fall back to a simpler method or return error

            # Constructing the prompt for the NL2SQL model
            # This prompt structure is generic; specific models might require different formatting.
            # For CodeT5, a common approach is to provide schema and then the question.
            prompt = f"Translate the following natural language query to SQL based on the provided Oracle database schema.\n"
            prompt += f"Database Schema:\n{serialized_schema}\n\n"
            prompt += f"Natural Language Query: {text}\nSQL Query:"

            inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=1024).to(self.device) # Max prompt length
            
            generated_ids = self.model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_length=self.max_length,
                num_beams=self.num_beams,
                temperature=self.temperature if self.temperature > 0 else None, # Temp must be > 0 for sampling
                do_sample=True if self.temperature > 0 else False,
                early_stopping=self.early_stopping,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
            
            sql_query = self.tokenizer.decode(generated_ids[0], skip_special_tokens=True)
            
            # Basic cleanup: some models might add "SQL Query:" or similar prefixes.
            sql_query = re.sub(r"^(SQL Query:|SQL:|Generated SQL:)\s*", "", sql_query, flags=re.IGNORECASE).strip()
            # Remove potential markdown backticks
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            # Ensure it's a SELECT statement as per problem constraints
            if not sql_query.upper().strip().startswith("SELECT"):
                logger.warning(f"Generated query is not a SELECT statement: {sql_query}")
                # Fallback or error, for now, try to make it SELECT if simple
                if "FROM" in sql_query.upper(): # very naive attempt
                    sql_query = "SELECT * " + sql_query


            is_valid = self._validate_sql(sql_query)
            
            # Confidence is not directly available from generate, placeholder
            confidence = 0.75 if is_valid and sql_query else 0.2

            result = {
                "sql": sql_query,
                "valid": is_valid,
                "confidence": confidence,
                "original_text": text,
                "prompt_used_schema_preview": serialized_schema[:200] + "..." # For debugging
            }
            
            if is_valid:
                logger.info(f"✅ Generated SQL: {sql_query}")
            else:
                logger.warning(f"⚠️ Invalid or empty SQL generated: '{sql_query}' for input '{text}'")
                result["error"] = "Generated SQL failed validation or was empty."
            
            return result
            
        except Exception as e:
            logger.error(f"❌ SQL generation failed: {e}", exc_info=True)
            return {
                "sql": "",
                "valid": False,
                "confidence": 0.0,
                "error": str(e),
                "original_text": text
            }
    
    def _validate_sql(self, sql: str) -> bool:
        """Basic SQL validation for safety."""
        if not sql or not sql.strip():
            return False
        
        sql_upper = sql.upper().strip()

        # Constraint: Only SELECT statements are allowed for this use case.
        if not sql_upper.startswith('SELECT'):
            logger.warning(f"Validation failed: Query does not start with SELECT. SQL: {sql}")
            return False
        
        # Block dangerous keywords, even within SELECT if they imply modification or harmful intent
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER', 'CREATE',
            'EXEC', 'SHUTDOWN', 'GRANT', 'REVOKE'
            # Add any other Oracle-specific keywords if necessary for security
        ]
        for keyword in dangerous_keywords:
            # Use regex to ensure keyword is standalone, not part of another word
            if re.search(r'\b' + keyword + r'\b', sql_upper):
                logger.warning(f"Validation failed: Dangerous keyword '{keyword}' found. SQL: {sql}")
                return False
        
        # Add more specific checks if needed, e.g., for comments that might hide malicious code, etc.
        # For now, ensuring it's a SELECT and doesn't contain overtly dangerous keywords.
        return True
    
    def get_sample_queries(self) -> List[str]:
        """Returns sample queries relevant to the new schema for testing."""
        # These should be updated to reflect the new Oracle schema
        return [
            "Show FIR registration number for petition ID 12345",
            "List all FIRs registered in Guntur district this year",
            "How many accused persons are juveniles in FIR number FIR001/2024?",
            "Find person details for person code 9876"
        ]

    def __del__(self):
        if hasattr(self, 'model') and self.model:
            del self.model
        if hasattr(self, 'tokenizer') and self.tokenizer:
            del self.tokenizer
        if self.device.type == 'cuda':
            torch.cuda.empty_cache()
            logger.info("Cleaned up NL2SQL model and CUDA cache.")