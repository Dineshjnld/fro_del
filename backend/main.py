"""
Backend API for CCTNS Copilot with Voice Integration
Combines Gemini API for NL2SQL with open-source voice models
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import tempfile
import os
from pathlib import Path
from typing import Optional
import asyncio

# Voice processing imports
try:
    from models.stt_processor import IndianSTTProcessor
    from models.text_processor import TextProcessor
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    print("⚠️ STT models not available. Voice input will be disabled.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CCTNS Copilot Backend",
    description="Voice-enabled backend for CCTNS database queries",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global processors
stt_processor = None
text_processor = None

@app.on_event("startup")
async def startup_event():
    """Initialize voice processors on startup"""
    global stt_processor, text_processor
    
    if STT_AVAILABLE:
        try:
            # Initialize STT processor with IndicConformer primary, Whisper fallback
            stt_config = {
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
            }
            
            stt_processor = IndianSTTProcessor(stt_config)
            
            # Initialize text processor
            text_config = {
                "grammar_correction": {
                    "name": "google/flan-t5-base"
                }
            }
            text_processor = TextProcessor(text_config)
            
            logger.info("✅ Voice processors initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize voice processors: {e}")
            stt_processor = None
            text_processor = None
    
    logger.info("🚀 CCTNS Copilot Backend started")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "voice_available": stt_processor is not None,
        "components": {
            "stt_processor": stt_processor is not None,
            "text_processor": text_processor is not None
        }
    }

@app.post("/api/voice/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(default="te"),
    enhance_text: bool = Form(default=True)
):
    """
    Transcribe audio file using IndicConformer (primary) or Whisper (fallback)
    """
    if not stt_processor:
        raise HTTPException(
            status_code=503, 
            detail="Voice processing not available. STT models not loaded."
        )
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file format
    allowed_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.webm']
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format {file_ext}. Allowed: {allowed_formats}"
        )
    
    # Save uploaded file temporarily
    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"audio_{file.filename}"
    
    try:
        # Save uploaded file
        with open(temp_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"🎤 Transcribing audio: {file.filename} (language: {language})")
        
        # Transcribe using STT processor
        transcription_result = await stt_processor.transcribe_audio(
            str(temp_file), 
            language
        )
        
        if not transcription_result.get("text"):
            return {
                "success": False,
                "error": "No speech detected in audio file",
                "suggestions": [
                    "Ensure audio is clear and audible",
                    "Check microphone volume",
                    "Try speaking closer to microphone"
                ]
            }
        
        # Enhance text if requested
        enhanced_result = {}
        if enhance_text and text_processor and transcription_result.get("text"):
            enhanced_result = await text_processor.process_text(
                transcription_result["text"],
                language
            )
        
        response = {
            "success": True,
            "transcription": {
                "text": transcription_result.get("text", ""),
                "confidence": transcription_result.get("confidence", 0.0),
                "language": transcription_result.get("language", language),
                "model_used": transcription_result.get("model_used", "unknown")
            },
            "file_info": {
                "filename": file.filename,
                "size": len(content),
                "format": file_ext
            }
        }
        
        # Add enhancement results if available
        if enhanced_result:
            response["enhancement"] = {
                "enhanced_text": enhanced_result.get("final", transcription_result["text"]),
                "corrections_applied": enhanced_result.get("corrections_applied", []),
                "confidence": enhanced_result.get("confidence", 0.8)
            }
            # Use enhanced text as the main result
            response["transcription"]["text"] = enhanced_result.get("final", transcription_result["text"])
        
        logger.info(f"✅ Transcription successful: {len(response['transcription']['text'])} characters")
        return response
        
    except Exception as e:
        logger.error(f"❌ Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        # Cleanup temporary file
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")

@app.post("/process-query")
async def process_query(request: dict):
    """
    Process query using Gemini API (frontend will handle this)
    This endpoint is for compatibility with the existing frontend
    """
    query_text = request.get("query", "")
    
    if not query_text:
        raise HTTPException(status_code=400, detail="No query text provided")
    
    # This will be handled by the frontend Gemini integration
    # Return a response that indicates frontend should handle it
    return {
        "success": True,
        "message": "Query received. Frontend should process with Gemini API.",
        "query": query_text,
        "use_frontend_processing": True
    }

@app.get("/api/voice/languages")
async def get_supported_languages():
    """Get supported languages for voice input"""
    return {
        "languages": [
            {
                "code": "te",
                "name": "Telugu",
                "native_name": "తెలుగు",
                "optimized": True
            },
            {
                "code": "hi", 
                "name": "Hindi",
                "native_name": "हिन्दी",
                "optimized": True
            },
            {
                "code": "en",
                "name": "English",
                "native_name": "English", 
                "optimized": True
            }
        ],
        "default": "te",
        "models": {
            "primary": "ai4bharat/indicconformer",
            "fallback": "openai/whisper-medium"
        }
    }

@app.get("/api/voice/status")
async def get_voice_status():
    """Get voice processing status"""
    return {
        "available": stt_processor is not None,
        "models_loaded": {
            "stt_processor": stt_processor is not None,
            "text_processor": text_processor is not None
        },
        "supported_formats": [".wav", ".mp3", ".m4a", ".ogg", ".webm"],
        "max_file_size": "50MB",
        "languages": ["te", "hi", "en"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)