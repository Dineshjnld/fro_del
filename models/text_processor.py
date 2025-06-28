"""
Text Processing using T5 models for grammar correction, translation, and enhancement.
"""
import torch
import logging
import re
import asyncio
from typing import Dict, List, Optional, Any
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, T5ForConditionalGeneration, T5Tokenizer
from config.settings import settings # Assuming settings.MODELS_DIR and settings.USE_GPU exist

logger = logging.getLogger(__name__)

# Language codes for IndicTrans2 model
INDIC_LANG_CODE_MAP = {
    "en": "eng_Latn", # Or handle separately if not using IndicTrans2 for en->en
    "te": "tel_Telu",
    "hi": "hin_Deva",
    # Add other supported Indic languages if needed
}
# Reverse map for model output if it uses full codes
INDIC_CODE_TO_LANG_MAP = {v: k for k, v in INDIC_LANG_CODE_MAP.items()}


class TextProcessor:
    """Text cleanup, enhancement, translation, and correction processor"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logger
        self.config = config.get("text_processing", {}) # Expecting the sub-config
        
        # Attempt to read USE_GPU from settings, default to True if not found
        use_gpu_setting = getattr(settings, 'USE_GPU', True)
        self.device = torch.device("cuda" if torch.cuda.is_available() and use_gpu_setting else "cpu")
        self.logger.info(f"TextProcessor using device: {self.device}")

        # Models for grammar correction
        self.correction_model_name = self.config.get("grammar_correction", {}).get("name", "google/flan-t5-base")
        self.correction_tokenizer = None
        self.correction_model = None
        self._load_correction_model()

        # Models for translation
        translation_config = self.config.get("translation", {})
        self.en_to_indic_model_name = translation_config.get("english_to_telugu", {}).get("name") # Name is generic now
        if not self.en_to_indic_model_name: # Fallback to old config structure
             self.en_to_indic_model_name = translation_config.get("english_to_indic", {}).get("name","ai4bharat/indictrans2-en-indic")

        self.indic_to_en_model_name = translation_config.get("telugu_to_english", {}).get("name")
        if not self.indic_to_en_model_name: # Fallback to old config structure
            self.indic_to_en_model_name = translation_config.get("indic_to_english", {}).get("name", "ai4bharat/indictrans2-indic-en")
        
        self.translation_tokenizers: Dict[str, AutoTokenizer] = {}
        self.translation_models: Dict[str, AutoModelForSeq2SeqLM] = {}
        self._load_translation_models()

        # Police terminology corrections (can be expanded from config)
        self.police_corrections = self.config.get("police_terminology", {}).get("corrections", {
            "fir": "FIR", "sho": "SHO", "station house officer": "SHO",
            "guntur": "Guntur", "vijayawada": "Vijayawada", # etc.
            # Transliterated terms that should map to English acronyms
            "ఎఫ్ఐఆర్": "FIR", "ఎఫ్‌ఐఆర్": "FIR", "ఎఫైఆర్": "FIR",
            "एफआईआर": "FIR",
        })
        self.common_speech_patterns = self.config.get("common_speech_patterns", {
            "show me": "show", "give me": "show", "tell me": "show",
            "how many": "count", "what is the total of": "count", "what is": "show",
        })

    def _load_model_generic(self, model_name: str, model_type: str = "seq2seq"):
        cache_dir = getattr(settings, 'MODELS_DIR', None)
        try:
            self.logger.info(f"Loading {model_type} model: {model_name}...")
            if model_type == "t5": # specifically for older T5Tokenizer usage if needed
                 tokenizer = T5Tokenizer.from_pretrained(model_name, cache_dir=cache_dir)
                 model = T5ForConditionalGeneration.from_pretrained(model_name, cache_dir=cache_dir)
            else: # AutoModel for most seq2seq
                 tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
                 model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=cache_dir)
            
            model.to(self.device)
            model.eval()
            self.logger.info(f"✅ {model_type.upper()} model '{model_name}' loaded on {self.device}")
            return tokenizer, model
        except Exception as e:
            self.logger.error(f"❌ Failed to load {model_type} model '{model_name}': {e}")
            return None, None

    def _load_correction_model(self):
        if self.correction_model_name:
            # Flan-T5 is a T5 model, can use T5 specific classes or Auto classes
            self.correction_tokenizer, self.correction_model = self._load_model_generic(self.correction_model_name, "t5")

    def _load_translation_models(self):
        if self.en_to_indic_model_name:
            tokenizer, model = self._load_model_generic(self.en_to_indic_model_name)
            if tokenizer and model:
                self.translation_tokenizers["en_to_indic"] = tokenizer
                self.translation_models["en_to_indic"] = model
        
        if self.indic_to_en_model_name:
            tokenizer, model = self._load_model_generic(self.indic_to_en_model_name)
            if tokenizer and model:
                self.translation_tokenizers["indic_to_en"] = tokenizer
                self.translation_models["indic_to_en"] = model

    async def translate_text(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Translate text from source_lang to target_lang"""
        if source_lang == target_lang:
            return text

        model_key = None
        if source_lang == "en" and target_lang in ["te", "hi"]:
            model_key = "en_to_indic"
        elif source_lang in ["te", "hi"] and target_lang == "en":
            model_key = "indic_to_en"

        if not model_key or model_key not in self.translation_models:
            self.logger.warning(f"No translation model available for {source_lang} to {target_lang}")
            return text # Return original text if no model

        tokenizer = self.translation_tokenizers[model_key]
        model = self.translation_models[model_key]

        src_lang_code = INDIC_LANG_CODE_MAP.get(source_lang, source_lang) # e.g. "tel_Telu"
        tgt_lang_code = INDIC_LANG_CODE_MAP.get(target_lang, target_lang) # e.g. "eng_Latn"

        # IndicTrans2 requires language token prefix. For some models, it's part of tokenizer.
        # For IndicTrans2, the tokenizer needs src_lang set.
        try:
            tokenizer.src_lang = src_lang_code
            # The input format for IndicTrans2 is just the text, src_lang and tgt_lang are handled by tokenizer/model config
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512).to(self.device)
            
            with torch.no_grad():
                # forced_bos_token_id for IndicTrans2 is set based on tgt_lang
                generated_tokens = model.generate(
                    **inputs,
                    forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang_code],
                    max_length=512, # Make configurable
                    num_beams=self.config.get("translation", {}).get(f"{source_lang}_to_{target_lang}", {}).get("num_beams", 5), # Beam size from config
                )
            translated_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            self.logger.info(f"Translated ({source_lang}->{target_lang}): '{text[:50]}' -> '{translated_text[:50]}'")
            return translated_text.strip()
        except Exception as e:
            self.logger.error(f"Translation error ({source_lang}->{target_lang}) for '{text[:50]}...': {e}")
            return text # Return original on error

    async def _grammar_correction(self, text: str, language: str = "en") -> str:
        """Use FLAN-T5 for grammar correction (primarily for English)"""
        if not self.correction_model or not self.correction_tokenizer or language != "en":
            # Only apply FLAN-T5 based correction if model is loaded and language is English
            if language != "en":
                self.logger.info(f"Skipping grammar correction for non-English text ({language}).")
            return text
        
        try:
            # FLAN-T5 prompt for grammar correction
            prompt = f"Correct the grammar and improve the clarity of the following English text, keeping the core meaning: \"{text}\""
            
            inputs = self.correction_tokenizer(
                prompt, return_tensors="pt", max_length=512, truncation=True, padding=True
            ).to(self.device)
            
            correction_params = self.config.get("grammar_correction", {})
            with torch.no_grad():
                outputs = self.correction_model.generate(
                    **inputs,
                    max_length=correction_params.get("max_length", 200),
                    min_length=correction_params.get("min_length", 10),
                    num_beams=correction_params.get("num_beams", 4),
                    temperature=float(correction_params.get("temperature", 0.5)), # Ensure float
                    early_stopping=correction_params.get("early_stopping", True),
                    # do_sample=True, # Temperature makes sense with do_sample=True
                )
            
            corrected = self.correction_tokenizer.decode(outputs[0], skip_special_tokens=True)
            self.logger.info(f"Grammar correction (en): '{text[:50]}' -> '{corrected[:50]}'")
            return corrected.strip()
        except Exception as e:
            self.logger.warning(f"Grammar correction failed for '{text[:50]}...': {e}")
            return text

    def _apply_static_corrections(self, text: str, lang: str = "en") -> str:
        """Apply pre-defined police terminology and common speech patterns."""
        corrected_text = text
        # Apply common speech patterns first (more general)
        for pattern, replacement in self.common_speech_patterns.items():
            corrected_text = re.sub(r'\b' + re.escape(pattern) + r'\b', replacement, corrected_text, flags=re.IGNORECASE)

        # Apply police terminology (more specific)
        # This part might be better if language specific, or applied to English text
        for term, replacement in self.police_corrections.items():
            corrected_text = re.sub(r'\b' + re.escape(term) + r'\b', replacement, corrected_text, flags=re.IGNORECASE)

        # Specific regex cleanups
        corrected_text = re.sub(r'\s+([.,?!"])', r'\1', corrected_text) # Remove space before punctuation
        corrected_text = re.sub(r'\s+', ' ', corrected_text).strip() # Normalize spaces
        return corrected_text

    async def process_text(self, raw_text: str, source_language: str = "en") -> Dict[str, Any]:
        """
        Process raw text: translate to English (if needed), correct, enhance.
        """
        self.logger.info(f"Processing text: '{raw_text[:50]}...' (source_lang: {source_language})")
        intermediate_text = raw_text
        original_text_for_grammar = raw_text # keep original for comparison if translated

        # Step 1: Translate to English if source is not English
        if source_language != "en":
            translated_to_english = await self.translate_text(raw_text, source_language, "en")
            if translated_to_english and translated_to_english != raw_text:
                intermediate_text = translated_to_english
                original_text_for_grammar = translated_to_english # grammar correction on translated text
                self.logger.info(f"Translated to English: '{intermediate_text[:50]}...'")
            else:
                self.logger.warning(f"Translation from {source_language} to English failed or no change for '{raw_text[:50]}...'")
                # Proceed with original text if translation fails

        # Step 2: Apply static corrections (common speech, police terms) on potentially translated English text
        # Some police terms might be language-specific, this assumes they are mostly English or mapped to English acronyms
        text_after_static_corrections = self._apply_static_corrections(intermediate_text, "en") # Apply on English text

        # Step 3: Grammar correction using FLAN-T5 (on English text)
        text_after_grammar_correction = await self._grammar_correction(text_after_static_corrections, "en")

        # Step 4: Query structure enhancement (simple regex, English based)
        # This step might be removed or made more robust if NL2SQL model handles it well
        # enhanced_text = self._enhance_query_structure(text_after_grammar_correction)
        final_text = self._final_cleanup(text_after_grammar_correction) # Use grammar corrected text for final cleanup

        # TODO: The confidence calculation and corrections_applied needs to be more robust
        return {
            "original": raw_text,
            "translated_to_english": intermediate_text if source_language != "en" else None,
            "static_corrected": text_after_static_corrections,
            "grammar_corrected_english": text_after_grammar_correction if source_language != "en" or raw_text != text_after_grammar_correction else None,
            "final_english_text": final_text, # This is the text intended for NL2SQL
            "source_language": source_language,
            "processing_steps": [
                f"Original: {raw_text}",
                f"Translated to English (if applicable): {intermediate_text if source_language != 'en' else 'N/A'}",
                f"After static corrections: {text_after_static_corrections}",
                f"After grammar correction: {text_after_grammar_correction}",
                f"Final processed (English): {final_text}"
            ]
            # "corrections_applied": [], # Needs better tracking
            # "confidence": 0.8 # Placeholder
        }

    def _enhance_query_structure(self, text: str) -> str:
        """DEPRECATED/SIMPLIFIED: Enhance query structure - NL2SQL model should handle most of this."""
        # This was quite rule-heavy and might conflict with a good NL2SQL model.
        # Kept minimal version for now, can be removed.
        enhanced = text.lower().strip()
        query_patterns = {
            r'^(show|display|list|get|find)\s+': r'SELECT ', # Basic SELECT hint
            r'^(count|how many|total)\s+': r'COUNT ',       # Basic COUNT hint
        }
        for pattern, replacement in query_patterns.items():
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        return enhanced.strip().capitalize() # Minimal change

    def _final_cleanup(self, text: str) -> str:
        """Final text cleanup on the (presumably) English text."""
        cleaned = text
        cleaned = re.sub(r'\s+', ' ', cleaned).strip() # Normalize spaces
        
        # Example: Capitalize common entities if needed, though NL2SQL might not require this.
        # For now, just basic space cleanup.
        # Proper noun capitalization can be tricky and language dependent.
        return cleaned

    async def batch_process(self, texts: List[str], source_language: str = "en") -> List[Dict[str, Any]]:
        """Process multiple texts in batch"""
        tasks = [self.process_text(text, source_language) for text in texts]
        return await asyncio.gather(*tasks)

# Example usage (for testing purposes)
if __name__ == '__main__':
    async def test_processor():
        # Mock settings for local testing
        class MockSettings:
            MODELS_DIR = "./models_cache_test"
            USE_GPU = False # Set to True if you have GPU and want to test
        
        global settings
        settings = MockSettings()
        Path(settings.MODELS_DIR).mkdir(parents=True, exist_ok=True)

        # Sample config similar to what would be loaded from YAML
        sample_config_full = {
            "text_processing": {
                "grammar_correction": {"name": "google/flan-t5-small"}, # smaller for faster test
                "translation": {
                    "english_to_telugu": {"name": "ai4bharat/indictrans2-en-indic"},
                    "telugu_to_english": {"name": "ai4bharat/indictrans2-indic-en"}
                },
                "police_terminology": {
                    "corrections": {"fir": "FIR", "ఎఫ్ఐఆర్": "FIR"}
                },
                "common_speech_patterns": {"show me": "show"}
            }
        }
        
        processor = TextProcessor(sample_config_full)
        
        test_texts = [
            ("show me fir for guntur", "en"),
            ("ఎఫ్ఐఆర్ చూపించండి", "te"), # "Show FIR" in Telugu
            ("मुझे एफआईआर दिखाओ", "hi"), # "Show me FIR" in Hindi
            ("what is the crimes today in vijayawada", "en"),
        ]
        
        for text, lang in test_texts:
            print(f"\n--- Processing: '{text}' (lang: {lang}) ---")
            result = await processor.process_text(text, source_language=lang)
            print(f"Original: {result.get('original')}")
            if result.get('translated_to_english'):
                print(f"Translated to English: {result.get('translated_to_english')}")
            print(f"Static Corrected: {result.get('static_corrected')}")
            if result.get('grammar_corrected_english'):
                print(f"Grammar Corrected (English): {result.get('grammar_corrected_english')}")
            print(f"Final English for NL2SQL: {result.get('final_english_text')}")
            print("Processing Steps:")
            for step in result.get("processing_steps", []):
                print(f"  - {step}")

            if lang == "en" and lang != "te": # Test en->te translation
                 translated_te = await processor.translate_text(result.get("final_english_text", text), "en", "te")
                 print(f"Test Translation (en->te): '{result.get('final_english_text', text)}' -> '{translated_te}'")

            if lang == "te": # Test te->en translation (already part of process_text)
                 pass # Covered by process_text

    asyncio.run(test_processor())