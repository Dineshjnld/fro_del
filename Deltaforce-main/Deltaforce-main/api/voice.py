"""
Voice Routes for CCTNS Copilot Engine
Handles speech-to-text operations and voice commands
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import JSONResponse
import logging
import os
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiofiles
import mimetypes
from datetime import datetime

# Import models (adjust imports based on your project structure)
try:
    from models.stt_processor import IndianSTTProcessor
    from models.text_processor import TextProcessor
    from config.settings import settings
except ImportError:
    # Fallback imports if structure is different
    from ...models.stt_processor import IndianSTTProcessor
    from ...models.text_processor import TextProcessor
    from ...config.settings import settings

# Create router
router = APIRouter(prefix="/voice", tags=["voice"])
logger = logging.getLogger(__name__)

# Global processor instances
stt_processor: Optional[IndianSTTProcessor] = None
text_processor: Optional[TextProcessor] = None

# Configuration
UPLOAD_DIR = "temp/audio"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_FORMATS = {
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3", 
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/x-wav": ".wav",
    "audio/x-m4a": ".m4a"
}

async def get_processors():
    """Initialize and get processor instances"""
    global stt_processor, text_processor
    
    if stt_processor is None or text_processor is None:
        try:
            import yaml
            
            # Load configuration
            config_path = "config/models_config.yaml"
            if not os.path.exists(config_path):
                # Fallback configuration
                config = {
                    "models": {
                        "speech_to_text": {
                            "primary_model": "ai4bharat/indicconformer",
                            "fallback_model": "openai/whisper-medium",
                            "confidence_threshold": 0.7
                        }
                    },
                    "text_processing": {
                        "enable_police_terms": True,
                        "enable_transliteration": True
                    }
                }
            else:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
            
            if stt_processor is None:
                stt_processor = IndianSTTProcessor(config["models"]["speech_to_text"])
                logger.info("✅ STT Processor initialized")
            
            if text_processor is None:
                text_processor = TextProcessor(config.get("text_processing", {}))
                logger.info("✅ Text Processor initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize processors: {e}")
            raise HTTPException(status_code=500, detail=f"Voice service initialization failed: {str(e)}")
    
    return stt_processor, text_processor

def validate_audio_file(file: UploadFile) -> Dict[str, Any]:
    """Validate uploaded audio file"""
    validation = {"valid": True, "errors": []}
    
    # Check file size
    if hasattr(file, 'size') and file.size > MAX_FILE_SIZE:
        validation["valid"] = False
        validation["errors"].append(f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB")
        return validation
    
    # Check file type
    content_type = file.content_type
    file_extension = Path(file.filename).suffix.lower() if file.filename else ""
    
    # Validate by content type or extension
    valid_content_type = content_type in SUPPORTED_FORMATS
    valid_extension = file_extension in SUPPORTED_FORMATS.values()
    
    if not (valid_content_type or valid_extension):
        validation["valid"] = False
        validation["errors"].append(f"Unsupported file format. Supported: {', '.join(SUPPORTED_FORMATS.values())}")
    
    # Check filename
    if not file.filename:
        validation["valid"] = False
        validation["errors"].append("Filename is required")
    
    return validation

async def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file and return path"""
    # Create upload directory
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = Path(file.filename).stem
    extension = Path(file.filename).suffix
    temp_filename = f"{original_name}_{timestamp}{extension}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)
    
    # Save file
    async with aiofiles.open(temp_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    return temp_path

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(default="te"),
    enhance_police_terms: bool = Form(default=True),
    include_confidence: bool = Form(default=True),
    include_alternatives: bool = Form(default=False)
):
    """
    Transcribe uploaded audio file to text
    
    - **file**: Audio file (wav, mp3, m4a, ogg, webm)
    - **language**: Language code (te=Telugu, hi=Hindi, en=English)
    - **enhance_police_terms**: Apply police terminology enhancements
    - **include_confidence**: Include confidence scores
    - **include_alternatives**: Include alternative transcriptions
    """
    
    temp_path = None
    
    try:
        # Get processors
        stt, text_proc = await get_processors()
        
        # Validate file
        validation = validate_audio_file(file)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["errors"])
        
        # Save uploaded file
        temp_path = await save_uploaded_file(file)
        
        # Get file info
        file_size = os.path.getsize(temp_path)
        
        logger.info(f"Processing audio file: {file.filename} ({file_size} bytes)")
        
        # Transcribe audio
        transcription_result = await stt.transcribe_audio(temp_path, language)
        
        if not transcription_result.get("text"):
            return {
                "success": False,
                "error": "No speech detected in audio file",
                "suggestions": [
                    "Check audio quality and volume",
                    "Ensure speech is clear and audible",
                    "Try a different audio format",
                    "Reduce background noise"
                ]
            }
        
        # Enhance with police terminology if requested
        if enhance_police_terms and transcription_result.get("text"):
            original_text = transcription_result["text"]
            enhanced_text = text_proc.normalize_police_terms(original_text)
            
            # Extract police entities
            entities = text_proc.extract_police_entities(enhanced_text)
            
            transcription_result.update({
                "original_text": original_text,
                "enhanced_text": enhanced_text,
                "entities": entities,
                "enhancement_applied": True
            })
        
        # Prepare response
        response = {
            "success": True,
            "text": transcription_result.get("enhanced_text", transcription_result.get("text")),
            "language": transcription_result.get("language", language),
            "model": transcription_result.get("model", "unknown"),
            "processing_time": transcription_result.get("processing_time", 0),
            "metadata": {
                "filename": file.filename,
                "file_size": file_size,
                "duration": transcription_result.get("duration"),
                "sample_rate": transcription_result.get("sample_rate")
            }
        }
        
        # Add confidence if requested
        if include_confidence:
            response["confidence"] = transcription_result.get("confidence", 0.0)
        
        # Add alternatives if requested
        if include_alternatives and "alternatives" in transcription_result:
            response["alternatives"] = transcription_result["alternatives"]
        
        # Add enhancement details
        if enhance_police_terms:
            response["enhancement"] = {
                "applied": transcription_result.get("enhancement_applied", False),
                "entities": transcription_result.get("entities", {}),
                "original_text": transcription_result.get("original_text")
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        # Cleanup temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError as e:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")

@router.post("/transcribe-batch")
async def transcribe_batch(
    files: List[UploadFile] = File(...),
    language: str = Form(default="te"),
    enhance_police_terms: bool = Form(default=True)
):
    """
    Transcribe multiple audio files in batch
    
    - **files**: List of audio files (max 10)
    - **language**: Language code for all files
    - **enhance_police_terms**: Apply police terminology enhancements
    """
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    try:
        stt, text_proc = await get_processors()
        
        results = []
        temp_paths = []
        
        # Process each file
        for idx, file in enumerate(files):
            temp_path = None
            try:
                # Validate file
                validation = validate_audio_file(file)
                if not validation["valid"]:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": validation["errors"][0] if validation["errors"] else "Validation failed"
                    })
                    continue
                
                # Save and transcribe
                temp_path = await save_uploaded_file(file)
                temp_paths.append(temp_path)
                
                transcription_result = await stt.transcribe_audio(temp_path, language)
                
                if transcription_result.get("text"):
                    text = transcription_result["text"]
                    
                    # Enhance if requested
                    if enhance_police_terms:
                        text = text_proc.normalize_police_terms(text)
                        entities = text_proc.extract_police_entities(text)
                    else:
                        entities = {}
                    
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "text": text,
                        "confidence": transcription_result.get("confidence", 0.0),
                        "language": transcription_result.get("language", language),
                        "entities": entities if enhance_police_terms else None
                    })
                else:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "No speech detected"
                    })
                    
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        # Cleanup all temp files
        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
        
        # Summary
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        return {
            "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@router.post("/transcribe-url")
async def transcribe_from_url(
    audio_url: str,
    language: str = "te",
    enhance_police_terms: bool = True
):
    """
    Transcribe audio from URL
    
    - **audio_url**: URL to audio file
    - **language**: Language code
    - **enhance_police_terms**: Apply police terminology enhancements
    """
    
    temp_path = None
    
    try:
        import httpx
        
        stt, text_proc = await get_processors()
        
        # Download audio file
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("audio/") and content_type not in SUPPORTED_FORMATS:
                raise HTTPException(status_code=400, detail="URL does not point to a supported audio file")
            
            # Check file size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="Audio file too large")
            
            # Save to temporary file
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_path = os.path.join(UPLOAD_DIR, f"url_audio_{timestamp}.wav")
            
            with open(temp_path, 'wb') as f:
                f.write(response.content)
        
        # Transcribe
        transcription_result = await stt.transcribe_audio(temp_path, language)
        
        if not transcription_result.get("text"):
            return {
                "success": False,
                "error": "No speech detected in audio file",
                "source_url": audio_url
            }
        
        # Enhance if requested
        text = transcription_result["text"]
        entities = {}
        
        if enhance_police_terms:
            text = text_proc.normalize_police_terms(text)
            entities = text_proc.extract_police_entities(text)
        
        return {
            "success": True,
            "text": text,
            "confidence": transcription_result.get("confidence", 0.0),
            "language": transcription_result.get("language", language),
            "source_url": audio_url,
            "entities": entities if enhance_police_terms else None,
            "metadata": {
                "model": transcription_result.get("model"),
                "processing_time": transcription_result.get("processing_time")
            }
        }
        
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
    except Exception as e:
        logger.error(f"URL transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": [
            {
                "code": "te",
                "name": "Telugu",
                "native_name": "తెలుగు",
                "region": "Andhra Pradesh, Telangana",
                "optimized_for": "Police operations in Telugu states"
            },
            {
                "code": "hi",
                "name": "Hindi",
                "native_name": "हिन्दी",
                "region": "India (National)",
                "optimized_for": "General police operations"
            },
            {
                "code": "en",
                "name": "English",
                "native_name": "English",
                "region": "International",
                "optimized_for": "Technical and official communications"
            },
            {
                "code": "en-IN",
                "name": "Indian English",
                "native_name": "Indian English",
                "region": "India",
                "optimized_for": "Indian police terminology and accents"
            }
        ],
        "default": "te",
        "recommendations": {
            "andhra_pradesh": "te",
            "telangana": "te",
            "other_states": "hi",
            "technical_reports": "en"
        }
    }

@router.get("/formats")
async def get_supported_formats():
    """Get list of supported audio formats"""
    return {
        "supported_formats": [
            {
                "format": "WAV",
                "extension": ".wav",
                "mime_type": "audio/wav",
                "recommended": True,
                "quality": "Lossless",
                "notes": "Best quality, larger file size"
            },
            {
                "format": "MP3",
                "extension": ".mp3", 
                "mime_type": "audio/mpeg",
                "recommended": True,
                "quality": "Compressed",
                "notes": "Good balance of quality and size"
            },
            {
                "format": "M4A",
                "extension": ".m4a",
                "mime_type": "audio/mp4",
                "recommended": False,
                "quality": "Compressed",
                "notes": "Apple format, good quality"
            },
            {
                "format": "OGG",
                "extension": ".ogg",
                "mime_type": "audio/ogg", 
                "recommended": False,
                "quality": "Compressed",
                "notes": "Open source format"
            },
            {
                "format": "WebM",
                "extension": ".webm",
                "mime_type": "audio/webm",
                "recommended": False,
                "quality": "Compressed",
                "notes": "Web optimized format"
            }
        ],
        "limits": {
            "max_file_size": f"{MAX_FILE_SIZE // (1024*1024)}MB",
            "max_batch_files": 10,
            "max_duration": "10 minutes (recommended)"
        },
        "recommendations": {
            "quality": "16kHz or higher sample rate",
            "channels": "Mono preferred for speech",
            "encoding": "PCM for WAV, 128kbps+ for MP3",
            "environment": "Quiet environment with minimal background noise"
        }
    }

@router.get("/status")
async def get_service_status():
    """Get voice service status and health check"""
    try:
        stt, text_proc = await get_processors()
        
        # Test basic functionality
        test_result = {"stt": "unknown", "text_processor": "unknown"}
        
        try:
            # Quick STT availability check
            if hasattr(stt, 'whisper_available') and stt.whisper_available:
                test_result["stt"] = "available"
            elif hasattr(stt, 'indic_available') and stt.indic_available:
                test_result["stt"] = "available" 
            else:
                test_result["stt"] = "limited"
        except:
            test_result["stt"] = "error"
        
        try:
            # Test text processor
            test_text = text_proc.clean_text("test")
            test_result["text_processor"] = "available" if test_text else "limited"
        except:
            test_result["text_processor"] = "error"
        
        return {
            "service": "online",
            "status": "healthy" if all(status == "available" for status in test_result.values()) else "degraded",
            "components": {
                "speech_to_text": {
                    "status": test_result["stt"],
                    "models": {
                        "primary": getattr(stt, 'indic_available', False),
                        "fallback": getattr(stt, 'whisper_available', False)
                    }
                },
                "text_processor": {
                    "status": test_result["text_processor"],
                    "police_terms": True,
                    "entity_extraction": True
                }
            },
            "features": {
                "languages": ["te", "hi", "en", "en-IN"],
                "batch_processing": True,
                "url_transcription": True,
                "police_terminology": True,
                "entity_extraction": True,
                "confidence_scoring": True
            },
            "limits": {
                "max_file_size_mb": MAX_FILE_SIZE // (1024*1024),
                "max_batch_files": 10,
                "supported_formats": len(SUPPORTED_FORMATS)
            },
            "uptime": "Available since service start",
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "service": "online",
            "status": "error",
            "error": str(e),
            "components": {
                "speech_to_text": {"status": "error"},
                "text_processor": {"status": "error"}
            }
        }

@router.get("/usage")
async def get_usage_statistics():
    """Get voice service usage statistics"""
    # In a real implementation, you'd track these metrics
    return {
        "statistics": {
            "total_transcriptions": 0,
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "total_processing_time": 0.0,
            "average_file_size": 0,
            "most_used_language": "te",
            "most_used_format": "wav"
        },
        "current_session": {
            "transcriptions": 0,
            "processing_time": 0.0,
            "session_start": datetime.now().isoformat()
        },
        "note": "Statistics tracking not yet implemented in this version"
    }