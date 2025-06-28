"""
Query Routes for CCTNS Copilot Engine
Handles natural language to SQL query processing
"""
from fastapi import APIRouter, HTTPException, Depends, Query as QueryParam
from fastapi.responses import JSONResponse
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import time
import uuid

# Import models (adjust based on your project structure)
try:
    from models.nl2sql_processor import NL2SQLProcessor
    from models.sql_executor import SQLExecutor
    from models.text_processor import TextProcessor
    from models.schema_manager import SchemaManager
    from config.settings import settings
except ImportError:
    from ...models.nl2sql_processor import NL2SQLProcessor
    from ...models.sql_executor import SQLExecutor
    from ...models.text_processor import TextProcessor
    from ...models.schema_manager import SchemaManager
    from ...config.settings import settings

router = APIRouter(prefix="/query", tags=["query"])
logger = logging.getLogger(__name__)

# Global instances
nl2sql_processor: Optional[NL2SQLProcessor] = None
sql_executor: Optional[SQLExecutor] = None
text_processor: Optional[TextProcessor] = None
schema_manager: Optional[SchemaManager] = None

# Request/Response models
class QueryRequest(BaseModel):
    text: str
    language: str = "en"
    context: Optional[Dict[str, Any]] = None
    execute: bool = True
    explain: bool = False
    limit: Optional[int] = 100

class ValidationRequest(BaseModel):
    sql: str

class QueryResponse(BaseModel):
    query_id: str
    original_query: str
    processed_query: Optional[str] = None
    sql: str
    valid: bool
    executed: bool = False
    results: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time: float = 0.0
    explanation: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None

async def get_processors():
    """Initialize and get processor instances"""
    global nl2sql_processor, sql_executor, text_processor, schema_manager
    
    if not all([nl2sql_processor, sql_executor, text_processor]):
        try:
            import yaml
            
            # Load configuration
            config_path = "config/models_config.yaml"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
            else:
                # Default configuration
                config = {
                    "cctns_schema": {},
                    "text_processing": {},
                    "database": {
                        "connection_string": settings.ORACLE_CONNECTION_STRING
                    }
                }
            
            if nl2sql_processor is None:
                nl2sql_processor = NL2SQLProcessor(config.get("cctns_schema", {}))
                logger.info("✅ NL2SQL Processor initialized")
            
            if sql_executor is None:
                sql_executor = SQLExecutor(settings.ORACLE_CONNECTION_STRING)
                logger.info("✅ SQL Executor initialized")
            
            if text_processor is None:
                text_processor = TextProcessor(config.get("text_processing", {}))
                logger.info("✅ Text Processor initialized")
            
            if schema_manager is None:
                schema_manager = SchemaManager(settings.ORACLE_CONNECTION_STRING)
                logger.info("✅ Schema Manager initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize query processors: {e}")
            raise HTTPException(status_code=500, detail=f"Query service unavailable: {str(e)}")
    
    return nl2sql_processor, sql_executor, text_processor, schema_manager

@router.post("/process", response_model=QueryResponse)
async def process_natural_language_query(request: QueryRequest):
    """
    Process natural language query end-to-end
    
    - **text**: Natural language query
    - **language**: Query language (en, hi, te)
    - **context**: Optional context information
    - **execute**: Whether to execute the generated SQL
    - **explain**: Whether to include query explanation
    - **limit**: Maximum number of results to return
    """
    
    start_time = time.time()
    query_id = f"query_{uuid.uuid4().hex[:8]}"
    
    try:
        nl2sql, sql_exec, text_proc, schema_mgr = await get_processors()
        
        # Preprocess text for SQL generation
        processed_text = text_proc.preprocess_for_sql(request.text)
        
        # Extract entities for better context
        entities = text_proc.extract_police_entities(request.text)
        
        # Generate SQL
        sql_result = await nl2sql.generate_sql(processed_text)
        
        response = QueryResponse(
            query_id=query_id,
            original_query=request.text,
            processed_query=processed_text,
            sql=sql_result.get("sql", ""),
            valid=sql_result.get("valid", False)
        )
        
        if not response.valid:
            response.errors = [sql_result.get("error", "SQL generation failed")]
            response.suggestions = await _generate_query_suggestions(request.text, entities)
            return response
        
        # Add SQL generation warnings
        if "warnings" in sql_result:
            response.warnings = sql_result.get("warnings", [])
        
        # Execute SQL if requested
        if request.execute and response.valid:
            # Apply limit if specified
            limited_sql = response.sql
            if request.limit and "LIMIT" not in response.sql.upper():
                if response.sql.strip().endswith(';'):
                    limited_sql = response.sql.rstrip(';') + f" FETCH FIRST {request.limit} ROWS ONLY"
                else:
                    limited_sql = response.sql + f" FETCH FIRST {request.limit} ROWS ONLY"
            
            exec_result = await sql_exec.execute_sql(limited_sql)
            
            response.executed = exec_result.get("success", False)
            if response.executed:
                response.results = exec_result.get("results", [])
                response.row_count = exec_result.get("row_count", 0)
                
                # Add execution warnings
                if response.warnings is None:
                    response.warnings = []
                response.warnings.extend(exec_result.get("warnings", []))
            else:
                response.errors = exec_result.get("errors", ["Query execution failed"])
        
        # Get query explanation if requested
        if request.explain and response.valid:
            try:
                explanation = sql_exec.explain_query(response.sql)
                if "error" not in explanation:
                    response.explanation = explanation
            except Exception as e:
                logger.warning(f"Query explanation failed: {e}")
        
        response.execution_time = time.time() - start_time
        
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.post("/validate")
async def validate_sql_query(request: ValidationRequest):
    """
    Validate SQL query without executing
    
    - **sql**: SQL query to validate
    """
    
    try:
        _, sql_exec, _, _ = await get_processors()
        
        validation = sql_exec.validate_sql(request.sql)
        
        return {
            "valid": validation["valid"],
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
            "security_issues": validation.get("security_issues", []),
            "performance_warnings": validation.get("performance_warnings", []),
            "query": request.sql
        }
        
    except Exception as e:
        logger.error(f"SQL validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.post("/explain")
async def explain_sql_query(request: ValidationRequest):
    """
    Get execution plan for SQL query
    
    - **sql**: SQL query to explain
    """
    
    try:
        _, sql_exec, _, _ = await get_processors()
        
        # Validate first
        validation = sql_exec.validate_sql(request.sql)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid SQL query",
                    "errors": validation["errors"],
                    "security_issues": validation.get("security_issues", [])
                }
            )
        
        explanation = sql_exec.explain_query(request.sql)
        
        if "error" in explanation:
            raise HTTPException(status_code=400, detail=explanation["error"])
        
        return {
            "sql": request.sql,
            "explanation": explanation,
            "estimated_cost": explanation.get("total_cost", 0),
            "estimated_rows": explanation.get("estimated_rows", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query explanation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")

@router.get("/suggestions")
async def get_query_suggestions(
    domain: str = QueryParam(default="general", description="Query domain"),
    language: str = QueryParam(default="en", description="Language for suggestions")
):
    """
    Get example queries for different domains
    
    - **domain**: Query domain (crime, officer, district, general, reports)
    - **language**: Language for suggestions (en, hi, te)
    """
    
    suggestions_en = {
        "crime": [
            "Show all crimes reported in Guntur district this month",
            "Count FIRs registered for theft in last 30 days", 
            "List murder cases in Visakhapatnam district",
            "Find all crimes involving vehicles this year",
            "Show crime trends by district for last quarter",
            "Display pending investigations for cyber crimes",
            "Count arrests made for drug-related offenses"
        ],
        "officer": [
            "List all officers in Guntur police station",
            "Show arrests made by Inspector Kumar",
            "Find officers with rank above Sub Inspector",
            "Count investigations handled by each SHO",
            "Show officer performance by district",
            "List officers posted in last 6 months",
            "Find officers with pending case assignments"
        ],
        "district": [
            "Compare crime rates across all districts",
            "Show police stations in Visakhapatnam district", 
            "List districts with highest crime rates this year",
            "Find district-wise officer distribution",
            "Show pending cases by district",
            "Display district population vs crime statistics",
            "Count police stations per district"
        ],
        "reports": [
            "Generate monthly crime summary report",
            "Create officer performance analysis",
            "Show district-wise crime comparison",
            "Generate case status report",
            "Create investigation progress summary",
            "Show evidence collection statistics",
            "Generate court case status report"
        ],
        "general": [
            "Show recent FIR registrations",
            "List pending investigations",
            "Find cases with court hearings this week",
            "Show evidence collected by case type",
            "Count total arrests this year",
            "Display system health statistics",
            "Show data quality metrics"
        ]
    }
    
    # Add Hindi/Telugu translations if needed
    suggestions_hi = {
        "crime": [
            "इस महीने गुंटूर जिले में रिपोर्ट किए गए सभी अपराध दिखाएं",
            "पिछले 30 दिनों में चोरी के लिए दर्ज FIR की गिनती करें"
        ],
        "officer": [
            "गुंटूर पुलिस स्टेशन के सभी अधिकारियों की सूची बनाएं"
        ]
    }
    
    if language == "hi":
        available_suggestions = suggestions_hi.get(domain, suggestions_en.get(domain, []))
    else:
        available_suggestions = suggestions_en.get(domain, suggestions_en["general"])
    
    return {
        "domain": domain,
        "language": language,
        "suggestions": available_suggestions,
        "available_domains": list(suggestions_en.keys()),
        "total_suggestions": len(available_suggestions)
    }

@router.get("/schema")
async def get_database_schema(table: Optional[str] = None):
    """
    Get database schema information
    
    - **table**: Optional specific table name
    """
    
    try:
        _, _, _, schema_mgr = await get_processors()
        
        if table:
            # Get specific table info
            table_info = schema_mgr.get_table_info(table)
            if "error" in table_info:
                raise HTTPException(status_code=404, detail=f"Table '{table}' not found")
            
            return {
                "table": table,
                "info": table_info,
                "related_tables": schema_mgr.get_related_tables(table)
            }
        else:
            # Get schema summary
            summary = schema_mgr.get_schema_summary()
            all_tables = schema_mgr.get_all_tables()
            
            return {
                "summary": summary,
                "tables": all_tables[:20],  # Limit for API response
                "total_tables": len(all_tables),
                "core_tables": [
                    "FIR", "DISTRICT_MASTER", "POLICE_STATION_MASTER",
                    "OFFICER_MASTER", "CRIME_TYPE_MASTER", "ARREST",
                    "INVESTIGATION", "EVIDENCE", "COURT_CASE"
                ],
                "note": "Use ?table=TABLE_NAME to get detailed table information"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Schema retrieval failed: {str(e)}")

@router.get("/history")
async def get_query_history(
    limit: int = QueryParam(default=10, ge=1, le=100, description="Number of queries to return")
):
    """
    Get recent query history
    
    - **limit**: Number of recent queries to return (1-100)
    """
    
    try:
        _, sql_exec, _, _ = await get_processors()
        
        history = sql_exec.get_query_history(limit)
        
        return {
            "history": history,
            "total_returned": len(history),
            "limit": limit,
            "note": "History shows actual database queries, not natural language inputs"
        }
        
    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        return {
            "history": [],
            "total_returned": 0,
            "error": "History not available",
            "details": str(e)
        }

@router.get("/examples")
async def get_query_examples():
    """Get comprehensive query examples with expected outputs"""
    
    return {
        "basic_queries": [
            {
                "natural_language": "Show all crimes in Guntur district",
                "expected_sql": "SELECT * FROM FIR f JOIN DISTRICT_MASTER d ON f.district_id = d.district_id WHERE d.district_name = 'Guntur'",
                "description": "Basic filtering by district"
            },
            {
                "natural_language": "Count FIRs registered this month",
                "expected_sql": "SELECT COUNT(*) FROM FIR WHERE EXTRACT(MONTH FROM date_reported) = EXTRACT(MONTH FROM SYSDATE)",
                "description": "Counting with date filtering"
            }
        ],
        "advanced_queries": [
            {
                "natural_language": "Show crime trends by district for last quarter",
                "expected_sql": "SELECT d.district_name, COUNT(*) as crime_count FROM FIR f JOIN DISTRICT_MASTER d ON f.district_id = d.district_id WHERE f.date_reported >= ADD_MONTHS(SYSDATE, -3) GROUP BY d.district_name ORDER BY crime_count DESC",
                "description": "Aggregation with time-based filtering"
            }
        ],
        "police_specific": [
            {
                "natural_language": "List all SHOs in Visakhapatnam",
                "expected_sql": "SELECT o.officer_name, ps.ps_name FROM OFFICER_MASTER o JOIN POLICE_STATION_MASTER ps ON o.officer_id = ps.sho_id JOIN DISTRICT_MASTER d ON ps.district_id = d.district_id WHERE d.district_name = 'Visakhapatnam'",
                "description": "Police hierarchy and location queries"
            }
        ],
        "tips": [
            "Use specific district names (Guntur, Visakhapatnam, etc.)",
            "Mention time periods clearly (this month, last quarter, etc.)",
            "Use police terminology (FIR, SHO, crime type, etc.)",
            "Be specific about what data you want to see"
        ]
    }

@router.get("/status")
async def get_query_service_status():
    """Get query service status and health check"""
    
    try:
        nl2sql, sql_exec, text_proc, schema_mgr = await get_processors()
        
        # Test database connection
        db_status = sql_exec.test_connection()
        
        # Get service statistics
        stats = sql_exec.get_statistics()
        
        return {
            "service": "online",
            "status": "healthy" if db_status["connected"] else "degraded",
            "database": {
                "connected": db_status["connected"],
                "connection_time": db_status.get("connection_time", 0),
                "engine": db_status.get("engine_info", "Unknown")
            },
            "processors": {
                "nl2sql": "available",
                "sql_executor": "available",
                "text_processor": "available",
                "schema_manager": "available"
            },
            "statistics": {
                "total_queries": stats["query_stats"]["total_queries"],
                "successful_queries": stats["query_stats"]["successful_queries"],
                "failed_queries": stats["query_stats"]["failed_queries"],
                "avg_execution_time": stats["query_stats"]["avg_execution_time"]
            },
            "features": {
                "natural_language_processing": True,
                "sql_validation": True,
                "query_explanation": True,
                "schema_introspection": True,
                "real_time_execution": True,
                "security_validation": True,
                "performance_analysis": True
            },
            "supported_languages": ["en", "hi", "te"],
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "service": "online",
            "status": "error",
            "error": str(e),
            "processors": {
                "nl2sql": "error",
                "sql_executor": "error", 
                "text_processor": "error",
                "schema_manager": "error"
            }
        }

async def _generate_query_suggestions(failed_query: str, entities: Dict[str, List[str]]) -> List[str]:
    """Generate helpful suggestions for failed queries"""
    
    suggestions = [
        "Try using simpler language",
        "Be more specific about the data you want",
        "Include location information (district, police station)",
        "Specify time periods clearly (this month, last year, etc.)",
        "Use police-specific terms (FIR, SHO, crime type, etc.)"
    ]
    
    query_lower = failed_query.lower()
    
    # Context-specific suggestions
    if "show" in query_lower or "display" in query_lower:
        suggestions.append("Try: 'List all [items] in [location]'")
    
    if "count" in query_lower or "how many" in query_lower:
        suggestions.append("Try: 'Count [items] registered [time period]'")
    
    if "officer" in query_lower:
        suggestions.append("Try: 'Show officers with rank [rank] in [location]'")
    
    if "crime" in query_lower:
        suggestions.append("Try: 'List crimes of type [type] in [district]'")
    
    # Entity-based suggestions
    if entities.get("locations"):
        suggestions.append(f"Detected location: {entities['locations'][0]} - be more specific about what data you want from this location")
    
    if entities.get("dates"):
        suggestions.append(f"Detected date: {entities['dates'][0]} - specify what you want to see for this date")
    
    if entities.get("officer_ranks"):
        suggestions.append(f"Detected rank: {entities['officer_ranks'][0]} - specify what information you need about this rank")
    
    return suggestions[:6]  # Limit to 6 suggestions