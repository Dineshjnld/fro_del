"""
CCTNS Copilot Engine API - Main Application
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from pathlib import Path
import yaml
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered copilot for CCTNS database queries"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist
static_dir = Path("web/static")
static_dir.mkdir(parents=True, exist_ok=True)

# Static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Global components
stt_processor = None
nl2sql_processor = None
sql_executor = None
report_generator = None

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global stt_processor, nl2sql_processor, sql_executor, report_generator
    
    try:
        logger.info("🚀 Starting CCTNS Copilot Engine...")
        
        # Load configuration with proper error handling
        config_path = Path("config/models_config.yaml")
        if not config_path.exists():
            config_path = Path("config/models_config.yml")
        
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Loaded configuration from {config_path}")
        else:
            logger.warning("⚠️ No models config file found, using defaults")
            config = _get_default_config()
        
        # Import models with error handling
        try:
            from models.stt_processor import IndianSTTProcessor
            from models.nl2sql_processor import NL2SQLProcessor
            from models.sql_executor import SQLExecutor
            from models.report_generator import ReportGenerator
        except ImportError as e:
            logger.error(f"❌ Failed to import models: {e}")
            logger.info("📦 Please ensure all model files are created")
            return
        
        # Initialize processors with error handling
        try:
            stt_processor = IndianSTTProcessor(config.get("speech_to_text", {}))
            logger.info("✅ STT Processor initialized")
        except Exception as e:
            logger.error(f"❌ STT Processor initialization failed: {e}")
            stt_processor = None
        
        try:
            nl2sql_processor = NL2SQLProcessor(config.get("cctns_schema", {}))
            logger.info("✅ NL2SQL Processor initialized")
        except Exception as e:
            logger.error(f"❌ NL2SQL Processor initialization failed: {e}")
            nl2sql_processor = None
        
        try:
            sql_executor = SQLExecutor(settings.ORACLE_CONNECTION_STRING)
            logger.info("✅ SQL Executor initialized")
        except Exception as e:
            logger.error(f"❌ SQL Executor initialization failed: {e}")
            sql_executor = None
        
        try:
            report_generator = ReportGenerator(config.get("summarization", {}))
            logger.info("✅ Report Generator initialized")
        except Exception as e:
            logger.error(f"❌ Report Generator initialization failed: {e}")
            report_generator = None
        
        logger.info("🚀 CCTNS Copilot Engine started successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        logger.warning("⚠️ Some components failed to initialize - server starting with limited functionality")

def _get_default_config():
    """Return default configuration when config file is not available"""
    return {
        "speech_to_text": {
            "primary": {
                "name": "ai4bharat/indicconformer",
                "confidence_threshold": 0.7,
                "device": "auto"
            },
            "fallback": {
                "name": "openai/whisper-medium",
                "confidence_threshold": 0.6,
                "device": "auto"
            }
        },
        "cctns_schema": {
            "database_type": "sqlite",
            "tables": []
        },
        "summarization": {
            "report_summary": {
                "name": "google/pegasus-cnn_dailymail",
                "max_length": 150,
                "min_length": 30
            }
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "components": {
            "stt_processor": stt_processor is not None,
            "nl2sql_processor": nl2sql_processor is not None,
            "sql_executor": sql_executor is not None,
            "report_generator": report_generator is not None
        }
    }
from fastapi.responses import FileResponse

@app.get("/ui")
async def serve_ui():
    """Serve the web UI"""
    return FileResponse("web/static/index.html")

@app.get("/")
async def root():
    """Root endpoint - redirect to UI"""
    return {
        "message": "Welcome to CCTNS Copilot Engine",
        "version": settings.VERSION,
        "status": "running",
        "web_ui": "/ui",
        "api_docs": "/docs",
        "health": "/health"
    }
# # Basic endpoints for testing
# @app.get("/")
# async def root():
#     """Root endpoint"""
#     return {
#         "message": "Welcome to CCTNS Copilot Engine",
#         "version": settings.VERSION,
#         "status": "running"
#     }

@app.post("/api/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...), language: str = "te"):
    """Transcribe voice input to text"""
    try:
        if not stt_processor:
            raise HTTPException(status_code=503, detail="STT Processor not available")
        
        # Save uploaded file
        file_path = f"temp/{file.filename}"
        Path("temp").mkdir(exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Transcribe
        result = await stt_processor.transcribe_audio(file_path, language)
        
        # Cleanup
        Path(file_path).unlink(missing_ok=True)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query/process")
async def process_query(query: dict):
    """Process natural language query end-to-end"""
    try:
        text = query.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No query text provided")
        
        # Generate SQL
        if nl2sql_processor:
            sql_result = await nl2sql_processor.generate_sql(text)
            if not sql_result.get("valid"):
                return {"error": "Could not generate valid SQL", "suggestion": "Try rephrasing your query"}
            
            # Execute SQL if executor is available
            if sql_executor:
                execution_result = await sql_executor.execute_query(sql_result["sql"])
                return {
                    "query": text,
                    "sql": sql_result["sql"],
                    "results": execution_result,
                    "success": True
                }
            else:
                return {
                    "query": text,
                    "sql": sql_result["sql"],
                    "message": "SQL generated but executor not available",
                    "success": True
                }
        else:
            return {"error": "NL2SQL processor not available"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)