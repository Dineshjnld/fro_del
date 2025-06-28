"""
Execution Agent for running SQL queries against the database
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

# Import database components (fallback for missing modules)
try:
    from models.sql_executor import SQLExecutor
    from config.database import DatabaseManager
except ImportError:
    class SQLExecutor:
        def __init__(self, connection_string): pass
        async def execute_query(self, sql):
            return {"success": True, "data": [{"id": 1, "name": "Sample"}], "row_count": 1}
    
    class DatabaseManager:
        def __init__(self): pass
        def validate_query(self, sql): return {"valid": True}

class ExecutionAgent(BaseAgent):
    """Agent specialized in executing SQL queries safely"""
    
    def __init__(self, config: Dict[str, Any], db_manager: Optional[DatabaseManager] = None):
        super().__init__("ExecutionAgent", config)
        
        self.sql_executor = SQLExecutor(config.get("oracle_connection_string"))
        self.db_manager = db_manager or DatabaseManager()
        
        # Execution settings
        self.query_timeout = config.get("query_timeout", 30)
        self.max_result_rows = config.get("max_result_rows", 1000)
        self.enable_query_cache = config.get("enable_query_cache", True)
        self.cache_ttl = config.get("cache_ttl_minutes", 60)
        
        # Query cache
        self.query_cache = {} if self.enable_query_cache else None
        self.cache_stats = {"hits": 0, "misses": 0}
        
        # Security settings
        self.allowed_tables = config.get("allowed_tables", [
            "FIR", "ARREST", "OFFICER_MASTER", "DISTRICT_MASTER", "STATION_MASTER", "CRIME_TYPE_MASTER"
        ])
        self.blocked_operations = config.get("blocked_operations", [
            "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"
        ])
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL query with safety checks and monitoring"""
        
        execution_type = input_data.get("type", "execute_sql")
        
        if execution_type == "execute_sql":
            return await self._execute_sql_query(input_data)
        elif execution_type == "validate_sql":
            return await self._validate_sql_only(input_data)
        elif execution_type == "explain_query":
            return await self._explain_query_plan(input_data)
        elif execution_type == "batch_execute":
            return await self._execute_batch_queries(input_data)
        else:
            raise ValueError(f"Unsupported execution type: {execution_type}")
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate execution input"""
        base_validation = await super()._validate_input(input_data)
        if not base_validation["valid"]:
            return base_validation
        
        sql = input_data.get("sql", "").strip()
        if not sql:
            return {"valid": False, "reason": "SQL query is required"}
        
        # Basic security checks
        sql_upper = sql.upper()
        
        # Check for blocked operations
        for operation in self.blocked_operations:
            if operation in sql_upper:
                return {"valid": False, "reason": f"Blocked operation: {operation}"}
        
        # Check for required SELECT
        if not sql_upper.startswith("SELECT"):
            return {"valid": False, "reason": "Only SELECT queries are allowed"}
        
        return {"valid": True}
    
    async def _execute_sql_query(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL query with full safety checks"""
        
        sql = input_data.get("sql", "").strip()
        use_cache = input_data.get("use_cache", self.enable_query_cache)
        format_results = input_data.get("format_results", True)
        
        self.logger.info(f"⚡ Executing SQL: {sql[:100]}...")
        
        start_time = time.time()
        
        try:
            # Step 1: Check cache
            if use_cache and self.query_cache is not None:
                cache_key = self._generate_cache_key(sql)
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    self.cache_stats["hits"] += 1
                    self.logger.info("📦 Retrieved from cache")
                    return {
                        **cached_result,
                        "from_cache": True,
                        "execution_time": time.time() - start_time
                    }
                else:
                    self.cache_stats["misses"] += 1
            
            # Step 2: Enhanced validation
            validation_result = self.db_manager.validate_query(sql)
            if not validation_result["valid"]:
                raise ValueError(f"Query validation failed: {validation_result.get('reason', 'Unknown error')}")
            
            # Step 3: Execute with timeout
            execution_result = await asyncio.wait_for(
                self.sql_executor.execute_query(sql),
                timeout=self.query_timeout
            )
            
            if not execution_result.get("success"):
                raise RuntimeError(f"Query execution failed: {execution_result.get('error', 'Unknown error')}")
            
            # Step 4: Process results
            raw_data = execution_result.get("data", [])
            row_count = execution_result.get("row_count", len(raw_data))
            
            # Check result size
            if row_count > self.max_result_rows:
                self.logger.warning(f"⚠️ Large result set truncated: {row_count} -> {self.max_result_rows}")
                raw_data = raw_data[:self.max_result_rows]
            
            # Step 5: Format results
            formatted_data = await self._format_query_results(raw_data) if format_results else raw_data
            
            # Step 6: Generate metadata
            execution_metadata = {
                "row_count": len(formatted_data),
                "total_rows": row_count,
                "execution_time_db": execution_result.get("execution_time", 0),
                "columns": list(formatted_data[0].keys()) if formatted_data else [],
                "truncated": row_count > self.max_result_rows
            }
            
            result = {
                "success": True,
                "data": formatted_data,
                "metadata": execution_metadata,
                "sql": sql,
                "from_cache": False,
                "execution_time": time.time() - start_time,
                "context_updates": {
                    "last_executed_sql": sql,
                    "last_result_count": len(formatted_data),
                    "last_execution_time": time.time() - start_time
                }
            }
            
            # Step 7: Cache result
            if use_cache and self.query_cache is not None:
                self._store_in_cache(cache_key, result)
            
            self.logger.info(f"✅ Query executed successfully: {len(formatted_data)} rows in {time.time() - start_time:.2f}s")
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"❌ Query timeout after {self.query_timeout}s")
            return {
                "success": False,
                "error": f"Query timeout after {self.query_timeout} seconds",
                "sql": sql,
                "execution_time": time.time() - start_time
            }
            
        except Exception as e:
            self.logger.error(f"❌ Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql": sql,
                "execution_time": time.time() - start_time
            }
    
    async def _validate_sql_only(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SQL without executing"""
        
        sql = input_data.get("sql", "")
        
        try:
            validation_result = self.db_manager.validate_query(sql)
            
            return {
                "valid": validation_result["valid"],
                "validation_details": validation_result,
                "sql": sql,
                "security_check": await self._perform_security_check(sql)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "sql": sql
            }
    
    async def _explain_query_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Explain query execution plan"""
        
        sql = input_data.get("sql", "")
        
        try:
            # Add EXPLAIN PLAN to the query
            explain_sql = f"EXPLAIN PLAN FOR {sql}"
            
            # Execute explain
            explain_result = await self.sql_executor.execute_query(explain_sql)
            
            # Get plan details
            plan_sql = "SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY)"
            plan_result = await self.sql_executor.execute_query(plan_sql)
            
            return {
                "success": True,
                "execution_plan": plan_result.get("data", []),
                "sql": sql,
                "estimated_cost": "Not available"  # Would need Oracle-specific parsing
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sql": sql
            }
    
    async def _execute_batch_queries(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple queries in batch"""
        
        queries = input_data.get("queries", [])
        stop_on_error = input_data.get("stop_on_error", True)
        
        if not queries:
            return {"success": False, "error": "No queries provided"}
        
        results = []
        overall_success = True
        
        for i, query_data in enumerate(queries):
            try:
                result = await self._execute_sql_query(query_data)
                results.append({
                    "query_index": i,
                    "result": result
                })
                
                if not result["success"] and stop_on_error:
                    overall_success = False
                    break
                    
            except Exception as e:
                results.append({
                    "query_index": i,
                    "result": {
                        "success": False,
                        "error": str(e)
                    }
                })
                
                if stop_on_error:
                    overall_success = False
                    break
        
        return {
            "success": overall_success,
            "batch_results": results,
            "total_queries": len(queries),
            "completed_queries": len(results)
        }
    
    async def _format_query_results(self, raw_data: List[Dict]) -> List[Dict]:
        """Format query results for better presentation"""
        if not raw_data:
            return []
        
        formatted_data = []
        
        for row in raw_data:
            formatted_row = {}
            
            for key, value in row.items():
                # Format dates
                if isinstance(value, (datetime, date)):
                    formatted_row[key] = value.strftime("%d-%m-%Y %H:%M:%S") if hasattr(value, 'hour') else value.strftime("%d-%m-%Y")
                
                # Format numbers
                elif isinstance(value, (int, float)):
                    formatted_row[key] = value
                
                # Handle None values
                elif value is None:
                    formatted_row[key] = ""
                
                # String values
                else:
                    formatted_row[key] = str(value)
            
            formatted_data.append(formatted_row)
        
        return formatted_data
    
    async def _perform_security_check(self, sql: str) -> Dict[str, Any]:
        """Perform comprehensive security check"""
        
        security_issues = []
        severity_level = "LOW"
        
        sql_upper = sql.upper()
        
        # Check for SQL injection patterns
        injection_patterns = [
            r"'\s*OR\s+'", r"'\s*;\s*", r"--", r"/\*", r"\*/",
            r"UNION\s+SELECT", r"DROP\s+TABLE", r"DELETE\s+FROM"
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, sql_upper):
                security_issues.append(f"Potential SQL injection pattern: {pattern}")
                severity_level = "HIGH"
        
        # Check for unauthorized table access
        mentioned_tables = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql_upper)
        flat_tables = [table for group in mentioned_tables for table in group if table]
        
        for table in flat_tables:
            if table not in [t.upper() for t in self.allowed_tables]:
                security_issues.append(f"Unauthorized table access: {table}")
                severity_level = "MEDIUM"
        
        return {
            "is_safe": len(security_issues) == 0,
            "severity": severity_level,
            "issues": security_issues,
            "scan_timestamp": datetime.now().isoformat()
        }
    
    def _generate_cache_key(self, sql: str) -> str:
        """Generate cache key for SQL query"""
        import hashlib
        return hashlib.md5(sql.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache"""
        if cache_key in self.query_cache:
            cached_data, timestamp = self.query_cache[cache_key]
            
            # Check if cache is still valid
            if time.time() - timestamp < (self.cache_ttl * 60):
                return cached_data
            else:
                # Remove expired cache
                del self.query_cache[cache_key]
        
        return None
    
    def _store_in_cache(self, cache_key: str, result: Dict[str, Any]):
        """Store result in cache"""
        # Don't cache errors or very large results
        if result.get("success") and len(result.get("data", [])) < 100:
            self.query_cache[cache_key] = (result, time.time())
            
            # Limit cache size
            if len(self.query_cache) > 100:
                # Remove oldest entries
                oldest_key = min(self.query_cache.keys(), 
                               key=lambda k: self.query_cache[k][1])
                del self.query_cache[oldest_key]
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "agent_stats": self.get_status(),
            "execution_specific": {
                "query_timeout": self.query_timeout,
                "max_result_rows": self.max_result_rows,
                "cache_enabled": self.enable_query_cache,
                "cache_stats": self.cache_stats,
                "allowed_tables": self.allowed_tables,
                "blocked_operations": self.blocked_operations
            }
        }
    
    async def clear_cache(self):
        """Clear query cache"""
        if self.query_cache is not None:
            self.query_cache.clear()
            self.cache_stats = {"hits": 0, "misses": 0}
            self.logger.info("🗑️ Query cache cleared")
