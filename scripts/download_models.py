"""
Download and cache required models
"""
import torch
import whisper
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from pathlib import Path
import logging

def download_models():
    """Download all required models"""
    models_dir = Path("models_cache")
    models_dir.mkdir(exist_ok=True)
    
    print("📥 Downloading models...")
    
    # 1. Whisper for STT
    print("Downloading Whisper...")
    whisper.load_model("medium", download_root=models_dir)
    
    # 2. FLAN-T5 for text processing
    print("Downloading FLAN-T5...")
    AutoTokenizer.from_pretrained("google/flan-t5-base", cache_dir=models_dir)
    AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base", cache_dir=models_dir)
    
    # 3. CodeT5 for SQL generation
    print("Downloading CodeT5...")
    AutoTokenizer.from_pretrained("Salesforce/codet5-base", cache_dir=models_dir)
    AutoModelForSeq2SeqLM.from_pretrained("Salesforce/codet5-base", cache_dir=models_dir)
    
    # 4. Pegasus for summarization
    print("Downloading Pegasus...")
    from transformers import PegasusTokenizer, PegasusForConditionalGeneration
    PegasusTokenizer.from_pretrained("google/pegasus-cnn_dailymail", cache_dir=models_dir)
    PegasusForConditionalGeneration.from_pretrained("google/pegasus-cnn_dailymail", cache_dir=models_dir)
    
    print("✅ All models downloaded successfully!")

if __name__ == "__main__":
    download_models()