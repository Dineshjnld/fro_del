"""
Query Agent for natural language to SQL conversion
"""
import re
import sqlparse
from typing import Dict, Any, List, Optional, Tuple
from .base_agent import BaseAgent

# Import processors (fallback for missing modules)
try:
    from models.nl2sql_processor import NL2SQLProcessor
    from models.schema_manager import SchemaManager
except ImportError:
    class NL2SQLProcessor:
        def __init__(self, config): pass
        async def generate_sql(self, text):
            return {"sql": "SELECT * FROM FIR LIMIT 10", "confidence": 0.8, "valid": True}
    
    class SchemaManager:
        def __init__(self, config): pass
        def get_table_info(self, table): return {"columns": ["id", "name"]}
        def get_all_tables(self): return ["FIR", "ARREST", "OFFICER_MASTER"]

class QueryAgent(BaseAgent):
    """Agent specialized in NL to SQL query generation"""
    
    def __init__(self, config: Dict[str, Any], schema_manager: Optional[SchemaManager] = None):
        super().__init__("QueryAgent", config)
        
        self.nl2sql_processor = NL2SQLProcessor(config.get("cctns_schema", {}))
        self.schema_manager = schema_manager or SchemaManager(config.get("cctns_schema", {}))
        
        # Query generation settings
        self.max_query_complexity = config.get("max_complexity", 10)
        self.allowed_operations = config.get("allowed_operations", ["SELECT"])
        self.blocked_keywords = config.get("blocked_keywords", [
            "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"
        ])
        self.max_result_limit = config.get("max_result_limit", 1000)
        
        # Query templates for common patterns
        self.query_templates = {
            "count": "SELECT COUNT(*) FROM {table} WHERE {conditions}",
            "list": "SELECT {columns} FROM {table} WHERE {conditions} LIMIT {limit}",
            "summary": "SELECT {group_by}, COUNT(*) as count FROM {table} WHERE {conditions} GROUP BY {group_by}",
            "join": "SELECT {columns} FROM {main_table} JOIN {join_table} ON {join_condition} WHERE {conditions}"
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process natural language query and generate SQL"""
        
        query_text = input_data.get("text", "")
        context = input_data.get("context", {})
        query_type = input_data.get("query_type", "standard")
        
        if query_type == "standard":
            return await self._generate_standard_query(query_text, context)
        elif query_type == "complex":
            return await self._generate_complex_query(query_text, context)
        elif query_type == "analytical":
            return await self._generate_analytical_query(query_text, context)
        elif query_type == "template":
            return await self._generate_template_query(query_text, context)
        else:
            raise ValueError(f"Unsupported query type: {query_type}")
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate query input"""
        base_validation = await super()._validate_input(input_data)
        if not base_validation["valid"]:
            return base_validation
        
        query_text = input_data.get("text", "").strip()
        if not query_text:
            return {"valid": False, "reason": "Query text is required"}
        
        if len(query_text) > 500:
            return {"valid": False, "reason": "Query text too long (max 500 characters)"}
        
        return {"valid": True}
    
    async def _generate_standard_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate standard SQL query"""
        
        self.logger.info(f"🔍 Generating SQL for: {query_text}")
        
        try:
            # Step 1: Preprocess query text
            processed_text = await self._preprocess_query_text(query_text)
            
            # Step 2: Generate SQL using NL2SQL processor
            sql_result = await self.nl2sql_processor.generate_sql(processed_text)
            
            if not sql_result.get("valid"):
                return {
                    "sql": "",
                    "confidence": 0.0,
                    "error": sql_result.get("error", "SQL generation failed"),
                    "suggestions": await self._get_query_suggestions(query_text),
                    "original_query": query_text
                }
            
            generated_sql = sql_result.get("sql", "")
            
            # Step 3: Validate and sanitize SQL
            validation_result = await self._validate_sql(generated_sql)
            if not validation_result["valid"]:
                return {
                    "sql": "",
                    "confidence": 0.0,
                    "error": f"Generated SQL validation failed: {validation_result['reason']}",
                    "suggestions": await self._get_query_suggestions(query_text),
                    "original_query": query_text
                }
            
            # Step 4: Add safety limits
            safe_sql = await self._add_safety_limits(generated_sql)
            
            # Step 5: Extract query metadata
            metadata = await self._extract_query_metadata(safe_sql)
            
            return {
                "sql": safe_sql,
                "confidence": sql_result.get("confidence", 0.0),
                "metadata": metadata,
                "original_query": query_text,
                "processed_query": processed_text,
                "estimated_rows": metadata.get("estimated_rows", 0),
                "context_updates": {
                    "last_generated_sql": safe_sql,
                    "last_query_type": "standard",
                    "tables_accessed": metadata.get("tables", [])
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ SQL generation failed: {e}")
            return {
                "sql": "",
                "confidence": 0.0,
                "error": str(e),
                "suggestions": await self._get_query_suggestions(query_text),
                "original_query": query_text
            }
    
    async def _generate_complex_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complex SQL with joins and aggregations"""
        
        self.logger.info(f"🔍 Generating complex SQL for: {query_text}")
        
        try:
            # Analyze query for complexity patterns
            complexity_analysis = await self._analyze_query_complexity(query_text)
            
            if complexity_analysis["complexity_score"] > self.max_query_complexity:
                return {
                    "sql": "",
                    "confidence": 0.0,
                    "error": f"Query too complex (score: {complexity_analysis['complexity_score']})",
                    "suggestions": ["Try breaking down the query into simpler parts"],
                    "original_query": query_text
                }
            
            # Generate base SQL
            standard_result = await self._generate_standard_query(query_text, context)
            
            if not standard_result.get("sql"):
                return standard_result
            
            # Enhance with complex features
            enhanced_sql = await self._enhance_sql_for_complexity(
                standard_result["sql"], 
                complexity_analysis
            )
            
            return {
                **standard_result,
                "sql": enhanced_sql,
                "complexity_analysis": complexity_analysis,
                "context_updates": {
                    **standard_result.get("context_updates", {}),
                    "last_query_type": "complex"
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Complex SQL generation failed: {e}")
            return {
                "sql": "",
                "confidence": 0.0,
                "error": str(e),
                "original_query": query_text
            }
    
    async def _generate_analytical_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytical SQL with aggregations and statistics"""
        
        self.logger.info(f"📊 Generating analytical SQL for: {query_text}")
        
        try:
            # Identify analytical patterns
            analytical_patterns = await self._identify_analytical_patterns(query_text)
            
            # Generate base query
            base_result = await self._generate_standard_query(query_text, context)
            
            if not base_result.get("sql"):
                return base_result
            
            # Transform to analytical query
            analytical_sql = await self._transform_to_analytical_sql(
                base_result["sql"], 
                analytical_patterns
            )
            
            return {
                **base_result,
                "sql": analytical_sql,
                "analytical_patterns": analytical_patterns,
                "context_updates": {
                    **base_result.get("context_updates", {}),
                    "last_query_type": "analytical"
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Analytical SQL generation failed: {e}")
            return {
                "sql": "",
                "confidence": 0.0,
                "error": str(e),
                "original_query": query_text
            }
    
    async def _generate_template_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQL using predefined templates"""
        
        # Identify template pattern
        template_match = await self._match_query_template(query_text)
        
        if not template_match:
            return await self._generate_standard_query(query_text, context)
        
        template_name = template_match["template"]
        parameters = template_match["parameters"]
        
        # Generate SQL from template
        template_sql = self.query_templates[template_name].format(**parameters)
        
        return {
            "sql": template_sql,
            "confidence": 0.9,
            "template_used": template_name,
            "parameters": parameters,
            "original_query": query_text,
            "context_updates": {
                "last_query_type": "template",
                "template_used": template_name
            }
        }
    
    async def _preprocess_query_text(self, query_text: str) -> str:
        """Preprocess and normalize query text"""
        # Convert to lowercase
        processed = query_text.lower().strip()
        
        # Expand common abbreviations
        abbreviations = {
            "fir": "first information report",
            "sho": "station house officer", 
            "asi": "assistant sub inspector",
            "si": "sub inspector"
        }
        
        for abbr, full in abbreviations.items():
            processed = re.sub(rf'\b{abbr}\b', full, processed)
        
        # Normalize district names
        district_corrections = {
            "guntur": "Guntur",
            "vijayawada": "Vijayawada", 
            "visakhapatnam": "Visakhapatnam"
        }
        
        for wrong, correct in district_corrections.items():
            processed = re.sub(rf'\b{wrong}\b', correct, processed, flags=re.IGNORECASE)
        
        return processed
    
    async def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate generated SQL for security and correctness"""
        try:
            # Parse SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                return {"valid": False, "reason": "Invalid SQL syntax"}
            
            statement = parsed[0]
            
            # Check for blocked keywords
            sql_upper = sql.upper()
            for keyword in self.blocked_keywords:
                if keyword in sql_upper:
                    return {"valid": False, "reason": f"Blocked keyword found: {keyword}"}
            
            # Check allowed operations
            if statement.get_type() not in self.allowed_operations:
                return {"valid": False, "reason": f"Operation not allowed: {statement.get_type()}"}
            
            # Validate table names against schema
            tables = self._extract_table_names(sql)
            available_tables = self.schema_manager.get_all_tables()
            
            for table in tables:
                if table.upper() not in [t.upper() for t in available_tables]:
                    return {"valid": False, "reason": f"Unknown table: {table}"}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "reason": f"SQL validation error: {str(e)}"}
    
    async def _add_safety_limits(self, sql: str) -> str:
        """Add safety limits to SQL queries"""
        sql_upper = sql.upper().strip()
        
        # Add LIMIT if not present and it's a SELECT
        if sql_upper.startswith("SELECT") and "LIMIT" not in sql_upper:
            sql += f" LIMIT {self.max_result_limit}"
        
        return sql
    
    async def _extract_query_metadata(self, sql: str) -> Dict[str, Any]:
        """Extract metadata from SQL query"""
        metadata = {
            "tables": self._extract_table_names(sql),
            "columns": self._extract_column_names(sql),
            "query_type": self._get_query_type(sql),
            "has_joins": "JOIN" in sql.upper(),
            "has_aggregations": any(func in sql.upper() for func in ["COUNT", "SUM", "AVG", "MIN", "MAX"]),
            "has_groupby": "GROUP BY" in sql.upper(),
            "has_orderby": "ORDER BY" in sql.upper(),
            "estimated_rows": self.max_result_limit
        }
        
        return metadata
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """Extract table names from SQL"""
        # Simple regex-based extraction
        patterns = [
            r'FROM\s+(\w+)',
            r'JOIN\s+(\w+)',
            r'UPDATE\s+(\w+)',
            r'INSERT\s+INTO\s+(\w+)'
        ]
        
        tables = []
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)
        
        return list(set(tables))
    
    def _extract_column_names(self, sql: str) -> List[str]:
        """Extract column names from SQL"""
        # Simple extraction - could be improved
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            columns_str = select_match.group(1)
            if columns_str.strip() == "*":
                return ["*"]
            
            columns = [col.strip() for col in columns_str.split(",")]
            return columns
        
        return []
    
    def _get_query_type(self, sql: str) -> str:
        """Get the type of SQL query"""
        sql_upper = sql.upper().strip()
        
        if sql_upper.startswith("SELECT"):
            return "SELECT"
        elif sql_upper.startswith("INSERT"):
            return "INSERT"
        elif sql_upper.startswith("UPDATE"):
            return "UPDATE"
        elif sql_upper.startswith("DELETE"):
            return "DELETE"
        else:
            return "UNKNOWN"
    
    async def _get_query_suggestions(self, query_text: str) -> List[str]:
        """Get suggestions for failed queries"""
        suggestions = []
        
        # Common suggestions based on query patterns
        if "count" in query_text.lower():
            suggestions.append("Try: 'How many FIRs were registered in Guntur?'")
        
        if "list" in query_text.lower() or "show" in query_text.lower():
            suggestions.append("Try: 'Show me recent FIRs from Krishna district'")
        
        if not any(table in query_text.upper() for table in ["FIR", "ARREST", "OFFICER", "DISTRICT"]):
            suggestions.append("Make sure to mention specific tables like FIR, ARREST, OFFICER_MASTER, etc.")
        
        suggestions.append("Use simpler language and be specific about what data you want")
        
        return suggestions
    
    async def _analyze_query_complexity(self, query_text: str) -> Dict[str, Any]:
        """Analyze query complexity"""
        complexity_score = 0
        factors = []
        
        # Check for multiple tables
        if len(re.findall(r'\b(FIR|ARREST|OFFICER|DISTRICT)\b', query_text.upper())) > 1:
            complexity_score += 2
            factors.append("multiple_tables")
        
        # Check for aggregations
        if any(word in query_text.lower() for word in ["count", "sum", "average", "total"]):
            complexity_score += 1
            factors.append("aggregations")
        
        # Check for time ranges
        if any(word in query_text.lower() for word in ["between", "from", "to", "during"]):
            complexity_score += 1
            factors.append("date_ranges")
        
        return {
            "complexity_score": complexity_score,
            "factors": factors,
            "is_complex": complexity_score > 3
        }
    
    async def _enhance_sql_for_complexity(self, base_sql: str, complexity_analysis: Dict[str, Any]) -> str:
        """Enhance SQL for complex requirements"""
        enhanced_sql = base_sql
        
        # Add appropriate JOINs if multiple tables detected
        if "multiple_tables" in complexity_analysis["factors"]:
            enhanced_sql = await self._add_intelligent_joins(enhanced_sql)
        
        return enhanced_sql
    
    async def _add_intelligent_joins(self, sql: str) -> str:
        """Add intelligent JOINs based on schema relationships"""
        # This would implement smart JOIN logic based on foreign key relationships
        # For now, return the original SQL
        return sql
    
    async def _identify_analytical_patterns(self, query_text: str) -> Dict[str, Any]:
        """Identify analytical patterns in query"""
        patterns = {
            "trend_analysis": bool(re.search(r'\b(trend|over time|monthly|yearly)\b', query_text.lower())),
            "comparison": bool(re.search(r'\b(compare|vs|versus|between)\b', query_text.lower())),
            "distribution": bool(re.search(r'\b(distribution|breakdown|by district|by type)\b', query_text.lower())),
            "ranking": bool(re.search(r'\b(top|highest|lowest|rank)\b', query_text.lower())),
            "percentage": bool(re.search(r'\b(percent|percentage|ratio)\b', query_text.lower()))
        }
        
        return {
            "patterns": patterns,
            "primary_pattern": max(patterns.keys(), key=lambda k: patterns[k]) if any(patterns.values()) else None
        }
    
    async def _transform_to_analytical_sql(self, base_sql: str, patterns: Dict[str, Any]) -> str:
        """Transform base SQL to analytical SQL"""
        # Add analytical enhancements based on identified patterns
        analytical_sql = base_sql
        
        primary_pattern = patterns.get("primary_pattern")
        
        if primary_pattern == "distribution":
            # Add GROUP BY for distribution analysis
            if "GROUP BY" not in analytical_sql.upper():
                analytical_sql = analytical_sql.replace("LIMIT", "GROUP BY district_id ORDER BY COUNT(*) DESC LIMIT")
        
        elif primary_pattern == "ranking":
            # Add ORDER BY for ranking
            if "ORDER BY" not in analytical_sql.upper():
                analytical_sql = analytical_sql.replace("LIMIT", "ORDER BY COUNT(*) DESC LIMIT")
        
        return analytical_sql
    
    async def _match_query_template(self, query_text: str) -> Optional[Dict[str, Any]]:
        """Match query against predefined templates"""
        query_lower = query_text.lower()
        
        # Count template
        if "how many" in query_lower or "count" in query_lower:
            table_match = re.search(r'\b(fir|arrest|officer)\b', query_lower)
            if table_match:
                return {
                    "template": "count",
                    "parameters": {
                        "table": table_match.group(1).upper(),
                        "conditions": "1=1"
                    }
                }
        
        # List template
        if "show" in query_lower or "list" in query_lower:
            table_match = re.search(r'\b(fir|arrest|officer)\b', query_lower)
            if table_match:
                return {
                    "template": "list", 
                    "parameters": {
                        "columns": "*",
                        "table": table_match.group(1).upper(),
                        "conditions": "1=1",
                        "limit": "10"
                    }
                }
        
        return None
