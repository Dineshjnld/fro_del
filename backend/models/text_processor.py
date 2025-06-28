"""
Text Processing for enhancing STT output
"""
import logging
import re
import asyncio
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class TextProcessor:
    """Text cleanup and enhancement processor"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Police terminology corrections
        self.police_corrections = {
            # Telugu terms
            "ఎఫ్ఐఆర్": "FIR",
            "ఎఫ్ఐఆర్లు": "FIRs", 
            "పోలీస్": "police",
            "స్టేషన్": "station",
            "గుంటూర్": "Guntur",
            "విజయవాడ": "Vijayawada",
            "విశాఖపట్నం": "Visakhapatnam",
            "తిరుపతి": "Tirupati",
            "కర్నూల్": "Kurnool",
            
            # Hindi terms  
            "एफआईआर": "FIR",
            "पुलिस": "police",
            "थाना": "station",
            "गुंटूर": "Guntur",
            "विजयवाड़ा": "Vijayawada",
            
            # English corrections
            "fir": "FIR",
            "firs": "FIRs",
            "sho": "SHO",
            "station house officer": "SHO",
            "guntur": "Guntur",
            "vijayawada": "Vijayawada",
            "visakhapatnam": "Visakhapatnam",
            "tirupati": "Tirupati",
            "kurnool": "Kurnool",
            
            # Common speech patterns
            "show me": "show",
            "give me": "show", 
            "tell me": "show",
            "how many": "count",
            "what is": "show"
        }
        
        logger.info("✨ TextProcessor initialized")
    
    async def process_text(self, raw_text: str, source_language: str = "en") -> Dict[str, str]:
        """
        Process and enhance raw text from STT
        """
        try:
            # Step 1: Apply police terminology corrections
            corrected_text = self._apply_police_corrections(raw_text)
            
            # Step 2: Clean and normalize
            cleaned_text = self._clean_text(corrected_text)
            
            # Step 3: Enhance query structure
            enhanced_text = self._enhance_query_structure(cleaned_text)
            
            # Step 4: Final cleanup
            final_text = self._final_cleanup(enhanced_text)
            
            return {
                "original": raw_text,
                "police_corrected": corrected_text,
                "cleaned": cleaned_text,
                "structure_enhanced": enhanced_text,
                "final": final_text,
                "corrections_applied": self._get_corrections_applied(raw_text, final_text),
                "confidence": self._calculate_confidence(raw_text, final_text)
            }
            
        except Exception as e:
            logger.error(f"Text processing error: {e}")
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
    
    def _clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        
        # Remove extra spaces again
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _enhance_query_structure(self, text: str) -> str:
        """Enhance query structure for better SQL generation"""
        enhanced = text.lower().strip()
        
        # Query type patterns
        query_patterns = {
            # Show/Display patterns
            r'^(show|display|list|get|find)\s+': r'show ',
            r'^count\s+': r'count ',
            r'^how many\s+': r'count ',
            r'^total\s+': r'count ',
            
            # Location patterns
            r'\s+in\s+([a-zA-Z]+)\s+(district|station)': r' in \1 \2',
            r'\s+from\s+([a-zA-Z]+)\s+(district|station)': r' from \1 \2',
        }
        
        for pattern, replacement in query_patterns.items():
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
        return enhanced.strip()
    
    def _final_cleanup(self, text: str) -> str:
        """Final text cleanup"""
        cleaned = text
        
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
        cleaned = cleaned.replace(" fir ", " FIR ")
        cleaned = cleaned.replace(" firs ", " FIRs ")
        cleaned = cleaned.replace(" sho ", " SHO ")
        
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
        
        return min(confidence, 1.0)