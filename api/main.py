"""
CCTNS Copilot Engine API - Main Application
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse # Added JSONResponse
import uvicorn
import logging
from pathlib import Path
import yaml
import sys
import os
import tempfile # Added
import asyncio # Added

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), "INFO"), # Provide default if LOG_LEVEL not in settings
    format=settings.LOG_FORMAT if hasattr(settings, 'LOG_FORMAT') else "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Ensure logs and temp directory exists
Path("logs").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True) # Ensure temp dir for audio files

app = FastAPI(
    title=settings.APP_NAME if hasattr(settings, 'APP_NAME') else "CCTNS Copilot Engine",
    version=settings.VERSION if hasattr(settings, 'VERSION') else "1.0.0",
    description="AI-powered copilot for CCTNS database queries"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Consider restricting this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist for the web/static UI
static_dir_path = Path("web/static")
static_dir_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir_path), name="static")


# Global components
stt_processor = None
text_processor = None # Added
nl2sql_processor = None
sql_executor = None
report_generator = None

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global stt_processor, text_processor, nl2sql_processor, sql_executor, report_generator
    
    try:
        logger.info("🚀 Starting CCTNS Copilot Engine...")
        
        config_path = Path("config/models_config.yaml")
        if not config_path.exists():
            config_path = Path("config/models_config.yml")
        
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Loaded configuration from {config_path}")
        else:
            logger.warning("⚠️ No models config file found at config/models_config.yaml or .yml, using defaults.")
            config = _get_default_config()
        
        # Import models
        try:
            from models.stt_processor import IndianSTTProcessor
            from models.text_processor import TextProcessor # Added
            from models.nl2sql_processor import NL2SQLProcessor
            from models.sql_executor import SQLExecutor
            from models.report_generator import ReportGenerator
        except ImportError as e:
            logger.error(f"❌ Failed to import core model processing modules: {e}")
            logger.info("📦 Please ensure all model files (stt_processor.py, text_processor.py, etc.) are created in the 'models' directory.")
            # Depending on severity, might want to exit or run with limited functionality
            return
        
        # Initialize STT Processor
        try:
            stt_config = config.get("speech_to_text", {})
            if not stt_config: logger.warning("Speech to text configuration not found or empty in config file.")
            stt_processor = IndianSTTProcessor(stt_config)
            logger.info(f"✅ STT Processor initialized with model: {stt_config.get('primary',{}).get('name','N/A')}")
        except Exception as e:
            logger.error(f"❌ STT Processor initialization failed: {e}")
            stt_processor = None
        
        # Initialize Text Processor
        try:
            tp_config = config.get("text_processing", {})
            if not tp_config: logger.warning("Text processing configuration not found or empty in config file.")
            text_processor = TextProcessor(tp_config) # Pass the text_processing sub-config
            logger.info(f"✅ Text Processor initialized with grammar model: {tp_config.get('grammar_correction',{}).get('name','N/A')}")
        except Exception as e:
            logger.error(f"❌ Text Processor initialization failed: {e}")
            text_processor = None

        # Initialize NL2SQL Processor
        try:
            nl2sql_config = config.get("nl2sql", {}) # NL2SQLProcessor might take schema from nl2sql or cctns_schema
            if 'cctns_schema' in config: # Prefer cctns_schema if available for NL2SQL
                nl2sql_config_to_pass = config.get("cctns_schema", {})
            else:
                nl2sql_config_to_pass = nl2sql_config

            if not nl2sql_config_to_pass: logger.warning("NL2SQL (or CCTNS Schema for it) configuration not found or empty.")
            nl2sql_processor = NL2SQLProcessor(nl2sql_config_to_pass)
            logger.info(f"✅ NL2SQL Processor initialized with model: {nl2sql_config.get('primary',{}).get('name','N/A')}")
        except Exception as e:
            logger.error(f"❌ NL2SQL Processor initialization failed: {e}")
            nl2sql_processor = None
        
        # Initialize SQL Executor
        try:
            db_connection_string = getattr(settings, 'ORACLE_CONNECTION_STRING', None)
            if not db_connection_string: logger.warning("ORACLE_CONNECTION_STRING not found in settings.")
            sql_executor = SQLExecutor(db_connection_string)
            logger.info("✅ SQL Executor initialized.")
        except Exception as e:
            logger.error(f"❌ SQL Executor initialization failed: {e}")
            sql_executor = None
        
        # Initialize Report Generator
        try:
            rg_config = config.get("summarization", {}) # ReportGenerator might use summarization config
            if not rg_config: logger.warning("Summarization configuration for Report Generator not found or empty.")
            report_generator = ReportGenerator(rg_config)
            logger.info(f"✅ Report Generator initialized with model: {rg_config.get('report_summary',{}).get('name','N/A')}")
        except Exception as e:
            logger.error(f"❌ Report Generator initialization failed: {e}")
            report_generator = None
        
        logger.info("🚀 CCTNS Copilot Engine startup sequence complete.")
        
    except Exception as e:
        logger.error(f"❌ Critical Startup failure: {e}", exc_info=True)
        # Exit if critical components fail to load, or set a flag to return errors on API calls
        # For now, it will start with components as None if they fail.

def _get_default_config():
    """Return minimal default configuration when config file is not available"""
    logger.info("Using default configurations as models_config.yml was not found.")
    return {
        "speech_to_text": {
            "primary": {"name": "ai4bharat/indicconformer", "confidence_threshold": 0.7, "device": "auto"},
            "fallback": {"name": "openai/whisper-medium", "confidence_threshold": 0.6, "device": "auto"}
        },
        "text_processing": { # Added default for text_processing
            "grammar_correction": {"name": "google/flan-t5-base"},
            "translation": {
                "english_to_indic": {"name": "ai4bharat/indictrans2-en-indic"},
                "indic_to_english": {"name": "ai4bharat/indictrans2-indic-en"}
            }
        },
        "nl2sql": { # Changed cctns_schema to nl2sql for consistency if NL2SQLProcessor expects this key
             "primary": {"name": "microsoft/CodeT5-base"} # Example
        },
        "summarization": {
            "report_summary": {"name": "google/pegasus-cnn_dailymail", "max_length": 150, "min_length": 30}
        }
    }

@app.get("/health")
async def health_check_endpoint(): # Renamed for clarity
    """Health check endpoint"""
    return {
        "status": "healthy", # Overall status, could be 'degraded' if some components fail
        "version": settings.VERSION if hasattr(settings, 'VERSION') else "1.0.0",
        "components": {
            "stt_processor": stt_processor is not None,
            "text_processor": text_processor is not None, # Added
            "nl2sql_processor": nl2sql_processor is not None,
            "sql_executor": sql_executor is not None,
            "report_generator": report_generator is not None
        }
    }

@app.get("/ui", include_in_schema=False) # exclude from OpenAPI docs if it's just serving UI
async def serve_ui_endpoint(): # Renamed for clarity
    """Serve the main web UI"""
    ui_path = static_dir_path / "index.html"
    if not ui_path.exists():
        logger.error(f"Web UI file not found at {ui_path}")
        return JSONResponse(status_code=404, content={"error": "Web UI not found. Please ensure 'web/static/index.html' exists."})
    return FileResponse(ui_path)

@app.get("/", include_in_schema=False) # exclude from OpenAPI docs
async def root_redirect(): # Renamed for clarity
    """Root endpoint - provides basic info and link to UI and API docs"""
    return {
        "message": f"Welcome to {settings.APP_NAME if hasattr(settings, 'APP_NAME') else 'CCTNS Copilot Engine'}",
        "version": settings.VERSION if hasattr(settings, 'VERSION') else "1.0.0",
        "status": "running",
        "web_ui_link": "/ui", # Link to the UI
        "api_documentation_link": "/docs" # Standard FastAPI docs
    }

@app.post("/api/voice/transcribe")
async def transcribe_voice_endpoint( # Renamed for clarity
    file: UploadFile = File(...),
    language: str = Form(default="te"),
    enhance_text: bool = Form(default=True) # From backend/main.py
):
    """
    Transcribe audio file, optionally enhance text (translate, correct).
    """
    if not stt_processor:
        raise HTTPException(status_code=503, detail="STT Processor not available.")
    if enhance_text and not text_processor: # Check if text_processor is needed but unavailable
        logger.warning("Text enhancement requested but Text Processor is not available.")
        # Optionally, proceed without enhancement or raise 503
        # For now, we'll proceed and enhancement step will be skipped.

    temp_dir = Path(tempfile.gettempdir())
    # Ensure unique filenames for concurrent requests if needed, though FastAPI handles requests separately
    temp_file_path = temp_dir / f"cctns_audio_{os.urandom(8).hex()}_{file.filename}"

    try:
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"🎤 Transcribing audio: {file.filename} (language: {language}, size: {len(content)} bytes)")
        
        stt_result = await stt_processor.transcribe_audio(str(temp_file_path), language)
        
        if not stt_result or not stt_result.get("text"):
            logger.warning(f"STT result empty for {file.filename}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "No speech detected or STT failed.",
                    "transcription": None
                }
            )

        transcribed_text = stt_result["text"]
        response_data = {
            "success": True,
            "transcription": {
                "text": transcribed_text,
                "language": stt_result.get("language", language), # Use STT detected language
                "confidence": stt_result.get("confidence"),
                "model_used": stt_result.get("model_used", "stt_primary")
            },
            "enhancement": None, # Initialize enhancement part
            "file_info": {"filename": file.filename, "size": len(content)}
        }

        if enhance_text and text_processor and transcribed_text:
            logger.info(f"Enhancing text for {file.filename} (source lang: {response_data['transcription']['language']})")
            # Pass STT's detected language to text_processor
            processed_text_details = await text_processor.process_text(
                transcribed_text,
                source_language=response_data['transcription']['language']
            )

            # Update transcription text with the final processed English text if available
            final_english_text = processed_text_details.get("final_english_text")
            if final_english_text:
                response_data["transcription"]["text"] = final_english_text
                # Indicate that this text is now processed and in English
                response_data["transcription"]["language"] = "en"
                response_data["transcription"]["is_processed_english"] = True

            response_data["enhancement"] = {
                "original_stt_text": transcribed_text,
                "original_stt_lang": stt_result.get("language", language),
                "translated_to_english": processed_text_details.get("translated_to_english"),
                "grammar_corrected_english": processed_text_details.get("grammar_corrected_english"),
                "static_corrected": processed_text_details.get("static_corrected"),
                # Any other details from process_text can be added here
            }
            logger.info(f"Text enhancement complete for {file.filename}. Final text: '{response_data['transcription']['text'][:50]}...'")

        return response_data
        
    except Exception as e:
        logger.error(f"❌ Voice transcription failed for {file.filename}: {e}", exc_info=True)
        # Ensure temp file is cleaned up even on error before raising HTTPException
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception as unlink_e:
                logger.error(f"Failed to cleanup temp file {temp_file_path} during error handling: {unlink_e}")
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")

    finally:
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file_path}: {e}")


@app.post("/api/query/process")
async def process_query_endpoint(query_request: dict): # Renamed for clarity, type hint for request body
    """
    Process natural language query: NL2SQL -> SQL Execution.
    Expects input like: {"text": "your query here"}
    The text should ideally be processed (translated to English, corrected)
    by calling /api/voice/transcribe first if it's from voice or non-English.
    """
    try:
        text = query_request.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Query text cannot be empty.")

        logger.info(f"Processing query: '{text[:100]}...'")

        if not nl2sql_processor:
            raise HTTPException(status_code=503, detail="NL2SQL Processor not available.")
        
        # Step 1: Generate SQL
        # Assuming 'text' is already in the target language for NL2SQL (e.g., English)
        sql_generation_result = await nl2sql_processor.generate_sql(text)

        if not sql_generation_result or not sql_generation_result.get("valid") or not sql_generation_result.get("sql"):
            logger.warning(f"NL2SQL failed for query: '{text}'. Result: {sql_generation_result}")
            error_msg = sql_generation_result.get("error", "Could not generate valid SQL from the query.")
            suggestion = sql_generation_result.get("suggestion", "Try rephrasing your query or be more specific.")
            return JSONResponse(
                status_code=400, # Or 500 if it's an internal NL2SQL error
                content={"success": False, "error": error_msg, "suggestion": suggestion, "sql": None, "results": None}
            )

        generated_sql = sql_generation_result["sql"]
        logger.info(f"Generated SQL for '{text[:50]}...': {generated_sql}")

        if not sql_executor:
            # If no executor, return the SQL and a message
            logger.warning("SQL Executor not available. Returning generated SQL without execution.")
            return {
                "query": text,
                "sql": generated_sql,
                "results": {"success": False, "message": "SQL Executor not available. Query not executed."},
                "success": True, # Overall operation succeeded in generating SQL
                "suggestion": "Database execution is currently offline."
            }
            
        # Step 2: Execute SQL
        logger.info(f"Executing SQL: {generated_sql}")
        execution_result = await sql_executor.execute_query(generated_sql)
        
        if not execution_result.get("success"):
            logger.error(f"SQL execution failed for SQL: '{generated_sql}'. Error: {execution_result.get('error')}")

        return {
            "query": text,
            "sql": generated_sql,
            "results": execution_result, # This contains {success, data, row_count, execution_time, error?, columns?}
            "success": execution_result.get("success", False), # Overall success depends on execution
            # Summary can be added here if ReportGenerator is used based on results
        }

    except HTTPException: # Re-raise HTTPExceptions
        raise
    except Exception as e:
        logger.error(f"❌ Query processing failed for text '{query_request.get('text','')[:100]}...': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

# --- New Endpoints from backend/main.py ---
@app.get("/api/voice/languages")
async def get_supported_voice_languages_endpoint(): # Renamed for clarity
    """Get supported languages for voice input, primarily for STT and TextProcessor."""
    # This can be dynamic based on loaded models or static as defined
    # The TextProcessor also has knowledge of languages it can handle for translation.
    # For now, returning a static list similar to backend/main.py
    # In a more dynamic setup, this could query STT/TextProcessor capabilities.
    return {
        "languages": [
            {"code": "en", "name": "English", "native_name": "English", "optimized": True},
            {"code": "te", "name": "Telugu", "native_name": "తెలుగు", "optimized": True},
            {"code": "hi", "name": "Hindi", "native_name": "हिन्दी", "optimized": True}
            # Add other languages supported by your STT/TextProcessing pipeline
        ],
        "default_stt_language": "te", # Example default
        "stt_models_info": { # Example of providing more info
            "primary": stt_processor.primary_model_name if stt_processor else "N/A",
            "fallback": stt_processor.fallback_model_name if stt_processor else "N/A"
        }
    }

@app.get("/api/voice/status")
async def get_voice_processing_status_endpoint(): # Renamed for clarity
    """Get status of voice processing components (STT and TextProcessor)."""
    return {
        "stt_available": stt_processor is not None,
        "text_processor_available": text_processor is not None,
        "models_loaded": { # More detailed status
            "stt_primary": stt_processor.primary_model is not None if stt_processor else False,
            "stt_fallback": stt_processor.fallback_model is not None if stt_processor else False,
            "text_correction": text_processor.correction_model is not None if text_processor else False,
            "text_translation_en_indic": text_processor.translation_models.get("en_to_indic") is not None if text_processor else False,
            "text_translation_indic_en": text_processor.translation_models.get("indic_to_en") is not None if text_processor else False,
        },
        "supported_audio_formats_example": [".wav", ".mp3", ".webm", ".ogg"], # Example
        "max_audio_file_size_mb_example": 50 # Example
    }
# --- End of New Endpoints ---

if __name__ == "__main__":
    app_host = getattr(settings, 'HOST', "0.0.0.0")
    app_port = int(getattr(settings, 'PORT', 8000))
    uvicorn.run(app, host=app_host, port=app_port)