"""
Speech-to-Text Processor for Indian languages using Hugging Face Transformers
"""
import logging
import asyncio
import torch
import librosa
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from transformers import (
    AutoProcessor,
    AutoModelForSpeechSeq2Seq,
    Wav2Vec2ForCTC,
    Wav2Vec2Processor
)
import time

logger = logging.getLogger(__name__)

# Language mapping for Whisper
WHISPER_LANGUAGE_MAP = {
    "en": "english",
    "hi": "hindi",
    "te": "telugu",
    # Add other mappings as needed
}

class IndianSTTProcessor:
    """Speech-to-Text Processor for Indian languages (Telugu, Hindi, English)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.primary_config = config.get("primary", {})
        self.fallback_config = config.get("fallback", {})
        self.supported_languages = ["te", "hi", "en", "auto"] # 'auto' primarily for Whisper

        self.device = self._get_device(self.primary_config.get("device", "auto"))
        logger.info(f"🎤 IndianSTTProcessor initialized. Using device: {self.device}")
        
        self.primary_model_name = self.primary_config.get("name")
        self.fallback_model_name = self.fallback_config.get("name")

        self.primary_model = None
        self.primary_processor = None
        self.fallback_model = None
        self.fallback_processor = None

        # Confidence thresholds (Note: CTC models like IndicConformer don't give straightforward confidence)
        self.primary_confidence_thresh = self.primary_config.get("confidence_threshold", 0.0) # Not directly applicable for CTC
        self.fallback_confidence_thresh = self.fallback_config.get("confidence_threshold", 0.6)


    def _get_device(self, device_preference: str) -> str:
        if device_preference == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if device_preference == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA specified but not available. Falling back to CPU.")
            return "cpu"
        return device_preference

    def _load_primary_model(self):
        if self.primary_model is None and self.primary_model_name:
            logger.info(f"Loading primary STT model: {self.primary_model_name}...")
            try:
                # IndicConformer is a Wav2Vec2 type model
                self.primary_processor = Wav2Vec2Processor.from_pretrained(self.primary_model_name)
                self.primary_model = Wav2Vec2ForCTC.from_pretrained(self.primary_model_name).to(self.device)
                logger.info(f"✅ Primary STT model {self.primary_model_name} loaded successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to load primary model {self.primary_model_name}: {e}")
                self.primary_model = None
                self.primary_processor = None
        return self.primary_model is not None

    def _load_fallback_model(self):
        if self.fallback_model is None and self.fallback_model_name:
            logger.info(f"Loading fallback STT model: {self.fallback_model_name}...")
            try:
                # Whisper is a SpeechSeq2Seq model
                self.fallback_processor = AutoProcessor.from_pretrained(self.fallback_model_name)
                self.fallback_model = AutoModelForSpeechSeq2Seq.from_pretrained(self.fallback_model_name).to(self.device)
                logger.info(f"✅ Fallback STT model {self.fallback_model_name} loaded successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to load fallback model {self.fallback_model_name}: {e}")
                self.fallback_model = None
                self.fallback_processor = None
        return self.fallback_model is not None

    async def _preprocess_audio(self, audio_path: str, target_sr: int = 16000) -> Optional[np.ndarray]:
        try:
            if not Path(audio_path).exists():
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            # Load audio file
            speech_array, sampling_rate = librosa.load(audio_path, sr=None, mono=True)
            
            # Resample if necessary
            if sampling_rate != target_sr:
                speech_array = librosa.resample(speech_array, orig_sr=sampling_rate, target_sr=target_sr)
            
            return speech_array
        except Exception as e:
            logger.error(f"Error preprocessing audio {audio_path}: {e}")
            return None

    async def transcribe_audio(self, audio_path: str, language: str = "auto") -> Dict[str, Any]:
        start_time = time.time()

        logger.info(f"🎵 Transcribing audio: {audio_path} (language: {language})")

        if not Path(audio_path).exists():
            return self._format_error_response(f"Audio file not found: {audio_path}", language, start_time)

        target_sr = 16000 # Common SR for many STT models
        speech_array = await self._preprocess_audio(audio_path, target_sr)

        if speech_array is None:
            return self._format_error_response("Audio preprocessing failed.", language, start_time)

        transcription_text = ""
        detected_language = language
        model_used_name = "None"
        confidence = 0.0 # Default, Whisper provides better confidence

        # Attempt with Primary Model (IndicConformer)
        if self._load_primary_model():
            logger.info(f"Attempting transcription with primary model: {self.primary_model_name}")
            try:
                inputs = self.primary_processor(speech_array, sampling_rate=target_sr, return_tensors="pt", padding=True)
                input_values = inputs.input_values.to(self.device)

                with torch.no_grad():
                    logits = self.primary_model(input_values).logits

                predicted_ids = torch.argmax(logits, dim=-1)
                transcription_text = self.primary_processor.batch_decode(predicted_ids)[0]
                model_used_name = self.primary_model_name
                # IndicConformer/Wav2Vec2 doesn't give a direct overall confidence score easily.
                # For simplicity, we'll assume if it transcribes, it's used.
                # More advanced: use segment probabilities if available or use fallback as a check.
                logger.info(f"Primary model transcription: '{transcription_text}'")

            except Exception as e:
                logger.error(f"❌ Primary model ({self.primary_model_name}) transcription failed: {e}")
                transcription_text = "" # Reset if primary failed

        # Attempt with Fallback Model (Whisper) if primary failed or text is empty
        # Or, if a confidence mechanism for primary was available and it was below threshold.
        # For now, if primary gives empty text, try fallback.
        if not transcription_text and self._load_fallback_model():
            logger.info(f"Primary model yielded no text or failed. Attempting with fallback model: {self.fallback_model_name}")
            try:
                # Whisper specific language code or None for auto-detect
                whisper_lang_code = WHISPER_LANGUAGE_MAP.get(language) if language != "auto" else None

                forced_bos_token_id = None
                if whisper_lang_code:
                    forced_bos_token_id = self.fallback_processor.tokenizer.lang_code_to_id.get(whisper_lang_code)
                    if not forced_bos_token_id:
                        logger.warning(f"Whisper language code for '{language}' ({whisper_lang_code}) not found in tokenizer. Using auto-detection.")


                input_features = self.fallback_processor(speech_array, sampling_rate=target_sr, return_tensors="pt").input_features.to(self.device)

                # Generate token ids
                # Whisper generate arguments can be taken from config if needed (temperature, beam_size etc.)
                generate_kwargs = {"language": whisper_lang_code} if whisper_lang_code and not forced_bos_token_id else {}
                if forced_bos_token_id : # Preferred way for Whisper multilingual
                     generate_kwargs["forced_decoder_ids"] = self.fallback_processor.get_decoder_prompt_ids(language=language, task="transcribe")


                predicted_ids = self.fallback_model.generate(input_features, **generate_kwargs)

                # Decode token ids to text
                transcription_text = self.fallback_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
                model_used_name = self.fallback_model_name

                # Whisper doesn't directly give overall confidence.
                # Confidence can be inferred from log probabilities of tokens if needed, but it's complex.
                # For now, we rely on the text output.
                # If Whisper was used, and language was 'auto', it might detect it.
                # This part is tricky as Whisper's `generate` doesn't directly return detected lang.
                # We assume if 'auto' was used, the output is in the dominant language.
                detected_language = language # Could be improved if Whisper provides lang detection info easily

                logger.info(f"Fallback model transcription: '{transcription_text}'")

                # Simple check for fallback confidence (if the text is too short, it might be noise)
                if len(transcription_text.split()) < 2 and self.fallback_confidence_thresh > 0: # Arbitrary check
                    logger.warning(f"Fallback transcription is very short. Confidence might be low.")
                    # In a real scenario, one might discard this if it's too short / non-sensical
                    confidence = 0.3 # Arbitrary low confidence
                else:
                    confidence = self.fallback_confidence_thresh + 0.2 # Assume it's okay if it passed this far

            except Exception as e:
                logger.error(f"❌ Fallback model ({self.fallback_model_name}) transcription failed: {e}")
                # Keep primary model's text if fallback also fails, unless primary was empty
                if not transcription_text: # if primary was also empty
                    return self._format_error_response(f"Both primary and fallback STT models failed. Last error: {e}", language, start_time)

        processing_time = time.time() - start_time

        if not transcription_text:
             logger.warning(f"⚠️ No transcription result from any model for {audio_path}")
             return self._format_error_response("No speech detected or models failed.", language, start_time, model_used_name)


        result = {
            "text": transcription_text.strip(),
            "confidence": confidence, # This is a placeholder, needs better mechanism
            "language": detected_language if detected_language != "auto" else "en", # Default to 'en' if auto
            "detected_language": detected_language if detected_language != "auto" else "en", # Placeholder
            "processing_time": round(processing_time, 3),
            "model_used": model_used_name,
            "audio_duration": round(len(speech_array) / target_sr, 3)
        }

        logger.info(f"✅ Transcription completed for {audio_path} in {result['processing_time']:.2f}s. Text: '{result['text'][:50]}...'")
        return result

    def _format_error_response(self, error_message: str, language: str, start_time: float, model_used:str = "None") -> Dict[str, Any]:
        processing_time = time.time() - start_time
        return {
            "text": "",
            "confidence": 0.0,
            "language": language,
            "error": error_message,
            "processing_time": round(processing_time, 3),
            "model_used": model_used
        }

    async def validate_audio(self, audio_path: str) -> Dict[str, Any]:
        """Validate audio file (basic check)"""
        try:
            file_path = Path(audio_path)
            if not file_path.exists():
                return {"valid": False, "error": "File not found"}
            
            # Basic check for file extension (can be expanded)
            supported_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm']
            if file_path.suffix.lower() not in supported_formats:
                return {"valid": False, "error": f"Unsupported format: {file_path.suffix}"}

            # Optionally, try to load it to see if it's a valid audio file
            try:
                y, sr = librosa.load(audio_path, sr=None, mono=True)
                duration = librosa.get_duration(y=y, sr=sr)
            except Exception as e:
                 return {"valid": False, "error": f"Cannot load audio file: {e}"}

            return {
                "valid": True,
                "file_size": file_path.stat().st_size,
                "format": file_path.suffix.lower(),
                "duration": duration
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def get_supported_languages(self) -> list:
        return self.supported_languages.copy()

    def __del__(self):
        # Ensure models are deleted from memory if GPU was used
        if hasattr(self, 'primary_model') and self.primary_model is not None:
            del self.primary_model
        if hasattr(self, 'primary_processor') and self.primary_processor is not None:
            del self.primary_processor
        if hasattr(self, 'fallback_model') and self.fallback_model is not None:
            del self.fallback_model
        if hasattr(self, 'fallback_processor') and self.fallback_processor is not None:
            del self.fallback_processor
        if self.device == 'cuda':
            torch.cuda.empty_cache()
            logger.info("Cleaned up STT models and CUDA cache.")