"""
Voice Agent for handling speech-to-text and voice processing
"""
import asyncio
import librosa
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

# Import processors (these would need to be implemented)
try:
    from models.stt_processor import IndianSTTProcessor
    from models.text_processor import TextProcessor
except ImportError:
    # Fallback for missing models
    class IndianSTTProcessor:
        def __init__(self, config): pass
        async def transcribe_audio(self, *args, **kwargs): 
            return {"text": "transcription placeholder", "confidence": 0.8}
    
    class TextProcessor:
        def __init__(self, config): pass
        async def enhance_text(self, *args, **kwargs):
            return {"enhanced_text": "enhanced placeholder", "corrections": []}

class VoiceAgent(BaseAgent):
    """Agent specialized in voice input processing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("VoiceAgent", config)
        
        # Initialize voice processors
        self.stt_processor = IndianSTTProcessor(config.get("speech_to_text", {}))
        self.text_processor = TextProcessor(config.get("text_processing", {}))
        
        # Voice-specific settings
        self.supported_languages = ["te", "hi", "en", "auto"]
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.max_audio_duration = config.get("max_audio_duration", 300)  # seconds
        self.supported_formats = [".wav", ".mp3", ".mp4", ".flac", ".ogg", ".webm"]
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process voice input through STT and text enhancement"""
        
        processing_type = input_data.get("type", "audio_file")
        
        if processing_type == "audio_file":
            return await self._process_audio_file(input_data)
        elif processing_type == "audio_stream":
            return await self._process_audio_stream(input_data)
        elif processing_type == "text_enhancement":
            return await self._process_text_enhancement(input_data)
        elif processing_type == "audio_validation":
            return await self._validate_audio_file(input_data)
        else:
            raise ValueError(f"Unsupported processing type: {processing_type}")
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate voice-specific input"""
        base_validation = await super()._validate_input(input_data)
        if not base_validation["valid"]:
            return base_validation
        
        processing_type = input_data.get("type", "audio_file")
        
        if processing_type == "audio_file":
            audio_path = input_data.get("audio_path")
            if not audio_path:
                return {"valid": False, "reason": "Audio path is required for audio_file type"}
            
            if not Path(audio_path).exists():
                return {"valid": False, "reason": f"Audio file not found: {audio_path}"}
            
            # Check file format
            file_ext = Path(audio_path).suffix.lower()
            if file_ext not in self.supported_formats:
                return {"valid": False, "reason": f"Unsupported audio format: {file_ext}"}
        
        elif processing_type == "text_enhancement":
            if not input_data.get("text"):
                return {"valid": False, "reason": "Text is required for text_enhancement type"}
        
        # Validate language
        language = input_data.get("language", "auto")
        if language not in self.supported_languages:
            return {"valid": False, "reason": f"Unsupported language: {language}"}
        
        return {"valid": True}
    
    async def _process_audio_file(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process uploaded audio file"""
        audio_path = input_data.get("audio_path")
        language = input_data.get("language", "auto")
        enhance_text = input_data.get("enhance_text", True)
        
        self.logger.info(f"🎤 Processing audio file: {audio_path}")
        
        try:
            # Step 1: Validate audio file
            audio_info = await self._get_audio_info(audio_path)
            if audio_info["duration"] > self.max_audio_duration:
                raise ValueError(f"Audio too long: {audio_info['duration']}s (max: {self.max_audio_duration}s)")
            
            # Step 2: Speech-to-Text
            stt_result = await self.stt_processor.transcribe_audio(audio_path, language)
            
            if stt_result.get("confidence", 0) < self.confidence_threshold:
                self.logger.warning(f"⚠️ Low confidence transcription: {stt_result.get('confidence')}")
            
            transcribed_text = stt_result.get("text", "")
            
            # Step 3: Text Enhancement (optional)
            enhanced_result = {}
            if enhance_text and transcribed_text:
                enhanced_result = await self.text_processor.enhance_text(
                    transcribed_text, 
                    language=language
                )
            
            # Step 4: Language Detection (if auto)
            detected_language = language
            if language == "auto":
                detected_language = stt_result.get("detected_language", "en")
            
            result = {
                "transcription": {
                    "text": transcribed_text,
                    "confidence": stt_result.get("confidence", 0.0),
                    "language": detected_language,
                    "segments": stt_result.get("segments", [])
                },
                "audio_info": audio_info,
                "processing_time": stt_result.get("processing_time", 0.0)
            }
            
            if enhanced_result:
                result["enhancement"] = {
                    "enhanced_text": enhanced_result.get("enhanced_text", transcribed_text),
                    "corrections": enhanced_result.get("corrections", []),
                    "grammar_score": enhanced_result.get("grammar_score", 0.0)
                }
            
            # Context updates for other agents
            result["context_updates"] = {
                "last_transcription": transcribed_text,
                "last_language": detected_language,
                "audio_processed": True
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Audio processing failed: {e}")
            raise
    
    async def _process_audio_stream(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process real-time audio stream"""
        # This would be implemented for real-time processing
        # For now, return a placeholder
        
        stream_data = input_data.get("stream_data")
        language = input_data.get("language", "auto")
        
        self.logger.info("🎙️ Processing audio stream")
        
        # Placeholder implementation
        return {
            "transcription": {
                "text": "Real-time transcription not yet implemented",
                "confidence": 0.0,
                "language": language,
                "is_final": False
            },
            "stream_info": {
                "chunks_processed": 0,
                "total_duration": 0.0
            }
        }
    
    async def _process_text_enhancement(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance existing text"""
        text = input_data.get("text", "")
        language = input_data.get("language", "auto")
        
        self.logger.info(f"✨ Enhancing text: {text[:50]}...")
        
        try:
            enhanced_result = await self.text_processor.enhance_text(text, language=language)
            
            return {
                "original_text": text,
                "enhanced_text": enhanced_result.get("enhanced_text", text),
                "corrections": enhanced_result.get("corrections", []),
                "grammar_score": enhanced_result.get("grammar_score", 0.0),
                "language": language,
                "context_updates": {
                    "last_enhanced_text": enhanced_result.get("enhanced_text", text)
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Text enhancement failed: {e}")
            raise
    
    async def _validate_audio_file(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate audio file without processing"""
        audio_path = input_data.get("audio_path")
        
        try:
            audio_info = await self._get_audio_info(audio_path)
            
            is_valid = True
            issues = []
            
            if audio_info["duration"] > self.max_audio_duration:
                is_valid = False
                issues.append(f"Audio too long: {audio_info['duration']}s")
            
            if audio_info["sample_rate"] < 8000:
                issues.append("Low sample rate may affect quality")
            
            return {
                "is_valid": is_valid,
                "audio_info": audio_info,
                "issues": issues
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "issues": ["Failed to analyze audio file"]
            }
    
    async def _get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get audio file information"""
        try:
            # Use librosa to get audio info
            duration = librosa.get_duration(filename=audio_path)
            y, sr = librosa.load(audio_path, sr=None)
            
            return {
                "duration": duration,
                "sample_rate": sr,
                "channels": 1 if y.ndim == 1 else y.shape[0],
                "file_size": Path(audio_path).stat().st_size,
                "format": Path(audio_path).suffix.lower()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get audio info: {e}")
            # Fallback to basic file info
            file_path = Path(audio_path)
            return {
                "duration": 0.0,
                "sample_rate": 0,
                "channels": 0,
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "format": file_path.suffix.lower()
            }
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return self.supported_languages.copy()
    
    async def get_audio_stats(self) -> Dict[str, Any]:
        """Get voice processing statistics"""
        return {
            "agent_stats": self.get_status(),
            "voice_specific": {
                "supported_languages": self.supported_languages,
                "confidence_threshold": self.confidence_threshold,
                "max_audio_duration": self.max_audio_duration,
                "supported_formats": self.supported_formats
            }
        }