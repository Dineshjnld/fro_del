"""
Text Processing using FLAN-T5 for grammar correction and enhancement
"""
import torch
import logging
import re
import asyncio
from typing import Dict, List, Optional
from transformers import T5Tokenizer, T5ForConditionalGeneration
from config.settings import settings

class TextProcessor:
    """Text cleanup and enhancement processor"""
    
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() and settings.USE_GPU else "cpu")
        
        # Load FLAN-T5 model
        self._load_model()
        
        # Police terminology corrections
        self.police_corrections = {
            # Telugu terms
            "ఎఫ్ఐఆర్": "FIR",
            "పోలీస్": "police",
            "స్టేషన్": "station",
            "గుంటూర్": "Guntur",
            "విజయవాడ": "Vijayawada",
            
            # Hindi terms  
            "एफआईआर": "FIR",
            "पुलिस": "police",
            "थाना": "station",
            
            # English corrections
            "fir": "FIR",
            "sho": "SHO",
            "station house officer": "SHO",
            "guntur": "Guntur",
            "vijayawada": "Vijayawada",
            "visakhapatnam": "Visakhapatnam",
            "tirupati": "Tirupati",
            "kurnool": "Kurnool",
            "nellore": "Nellore",
            "kadapa": "Kadapa",
            "chittoor": "Chittoor",
            
            # Common speech patterns
            "show me": "show",
            "give me": "show", 
            "tell me": "show",
            "how many": "count",
            "what is": "show",
            "crimes are": "crimes",
            "officers are": "officers"
        }
    
    def _load_model(self):
        """Load FLAN-T5 model for text processing"""
        try:
            model_name = self.config.get("grammar_correction", {}).get("name", "google/flan-t5-base")
            
            self.tokenizer = T5Tokenizer.from_pretrained(
                model_name,
                cache_dir=settings.MODELS_DIR
            )
            self.model = T5ForConditionalGeneration.from_pretrained(
                model_name,
                cache_dir=settings.MODELS_DIR
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            self.logger.info(f"✅ FLAN-T5 text processor loaded on {self.device}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load text processor: {e}")
            self.model = None
            self.tokenizer = None
    
    async def process_text(self, raw_text: str, source_language: str = "en") -> Dict[str, str]:
        """
        Process and enhance raw text from STT
        
        Args:
            raw_text: Raw transcribed text
            source_language: Source language (te, hi, en)
            
        Returns:
            Dict with original, enhanced, and correction details
        """
        try:
            # Step 1: Apply police terminology corrections
            corrected_text = self._apply_police_corrections(raw_text)
            
            # Step 2: Grammar correction using FLAN-T5
            if self.model and self.tokenizer:
                grammar_corrected = await self._grammar_correction(corrected_text)
            else:
                grammar_corrected = corrected_text
            
            # Step 3: Query structure enhancement
            enhanced_text = self._enhance_query_structure(grammar_corrected)
            
            # Step 4: Final cleanup
            final_text = self._final_cleanup(enhanced_text)
            
            return {
                "original": raw_text,
                "police_corrected": corrected_text,
                "grammar_corrected": grammar_corrected,
                "structure_enhanced": enhanced_text,
                "final": final_text,
                "corrections_applied": self._get_corrections_applied(raw_text, final_text),
                "confidence": self._calculate_confidence(raw_text, final_text)
            }
            
        except Exception as e:
            self.logger.error(f"Text processing error: {e}")
            return {
                "original": raw_text,
                "final": raw_text,
                "error": str(e),
                "confidence": 0.5
            }
    
    def _apply_police_corrections(self, text: str) -> str:
        """Apply police domain terminology corrections"""
        corrected = text
        
        for incorrect, correct in self.police_corrections.items():
            # Case-insensitive replacement
            corrected = re.sub(
                re.escape(incorrect), 
                correct, 
                corrected, 
                flags=re.IGNORECASE
            )
        
        return corrected.strip()
    
    async def _grammar_correction(self, text: str) -> str:
        """Use FLAN-T5 for grammar correction"""
        try:
            # Create grammar correction prompt
            prompt = f"Fix grammar and make this police query clearer: {text}"
            
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=200,
                    num_beams=4,
                    temperature=0.3,
                    do_sample=True,
                    early_stopping=True,
                    pad_token_id=self.tokenizer.pad_token_id
                )
            
            corrected = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove the prompt from output if present
            if corrected.startswith("Fix grammar"):
                corrected = corrected.split(":", 1)[-1].strip()
            
            return corrected
            
        except Exception as e:
            self.logger.warning(f"Grammar correction failed: {e}")
            return text
    
    def _enhance_query_structure(self, text: str) -> str:
        """Enhance query structure for better SQL generation"""
        enhanced = text.lower().strip()
        
        # Query type patterns
        query_patterns = {
            # Show/Display patterns
            r'^(show|display|list|get|find)\s+': r'SELECT ',
            r'^count\s+': r'COUNT ',
            r'^how many\s+': r'COUNT ',
            r'^total\s+': r'COUNT ',
            
            # Add WHERE clause hints
            r'\s+in\s+([a-zA-Z]+)\s+(district|station)': r' WHERE \2 = "\1"',
            r'\s+for\s+([a-zA-Z]+)\s+(officer|station)': r' WHERE \2 = "\1"',
            r'\s+by\s+([a-zA-Z\s]+)\s+(officer|station)': r' WHERE \2 = "\1"',
            
            # Time patterns
            r'\s+today\b': r' WHERE DATE = TODAY',
            r'\s+this\s+month\b': r' WHERE MONTH = CURRENT_MONTH',
            r'\s+last\s+month\b': r' WHERE MONTH = LAST_MONTH',
            r'\s+this\s+year\b': r' WHERE YEAR = CURRENT_YEAR'
        }
        
        for pattern, replacement in query_patterns.items():
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
        return enhanced.strip()
    
    def _final_cleanup(self, text: str) -> str:
        """Final text cleanup"""
        cleaned = text
        
        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Capitalize proper nouns
        districts = ["guntur", "vijayawada", "visakhapatnam", "tirupati", "kurnool"]
        for district in districts:
            cleaned = re.sub(
                rf'\b{district}\b', 
                district.title(), 
                cleaned, 
                flags=re.IGNORECASE
            )
        
        # Fix common patterns
        cleaned = cleaned.replace(" FIR ", " FIR ")
        cleaned = cleaned.replace(" SHO ", " SHO ")
        
        return cleaned.strip()
    
    def _get_corrections_applied(self, original: str, final: str) -> List[str]:
        """Get list of corrections applied"""
        corrections = []
        
        if original.lower() != final.lower():
            corrections.append(f"Enhanced: '{original}' → '{final}'")
        
        # Check for specific corrections
        for term, replacement in self.police_corrections.items():
            if term.lower() in original.lower() and replacement in final:
                corrections.append(f"Police term: '{term}' → '{replacement}'")
        
        return corrections
    
    def _calculate_confidence(self, original: str, final: str) -> float:
        """Calculate confidence in text processing"""
        # Base confidence
        confidence = 0.8
        
        # Boost if police terms were corrected
        police_terms_found = sum(1 for term in self.police_corrections.keys() 
                               if term.lower() in original.lower())
        confidence += min(police_terms_found * 0.05, 0.15)
        
        # Boost if structure was enhanced
        if any(word in final.upper() for word in ["SELECT", "COUNT", "WHERE"]):
            confidence += 0.05
        
        return min(confidence, 1.0)

    async def batch_process(self, texts: List[str]) -> List[Dict[str, str]]:
        """Process multiple texts in batch"""
        tasks = [self.process_text(text) for text in texts]
        return await asyncio.gather(*tasks)