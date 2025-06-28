"""
CCTNS Copilot Engine Configuration
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings:
    """Application settings class"""
    
    def __init__(self):
        # Load from environment variables or use defaults
        
        # Application
        self.APP_NAME = os.getenv("APP_NAME", "CCTNS Copilot Engine")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        
        # Server
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))
        
        # Database - Use SQLite for demo if Oracle not available
        self.ORACLE_CONNECTION_STRING = os.getenv(
            "ORACLE_CONNECTION_STRING", 
            "sqlite:///./cctns_demo.db"
        )
        self.DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        self.DATABASE_TIMEOUT = int(os.getenv("DATABASE_TIMEOUT", "30"))
        
        # Models Configuration
        self.MODELS_DIR = Path(os.getenv("MODELS_DIR", "./models_cache"))
        self.USE_GPU = os.getenv("USE_GPU", "false").lower() == "true"
        
        # Speech-to-Text
        self.STT_MODEL_PRIMARY = os.getenv("STT_MODEL_PRIMARY", "ai4bharat/indicconformer")
        self.STT_MODEL_FALLBACK = os.getenv("STT_MODEL_FALLBACK", "openai/whisper-medium")
        self.STT_LANGUAGE_DEFAULT = os.getenv("STT_LANGUAGE_DEFAULT", "te")
        self.STT_CONFIDENCE_THRESHOLD = float(os.getenv("STT_CONFIDENCE_THRESHOLD", "0.7"))
        
        # Text Processing
        self.TEXT_CLEANUP_MODEL = os.getenv("TEXT_CLEANUP_MODEL", "google/flan-t5-base")
        self.TEXT_MAX_LENGTH = int(os.getenv("TEXT_MAX_LENGTH", "512"))
        
        # SQL Generation
        self.NL2SQL_MODEL = os.getenv("NL2SQL_MODEL", "microsoft/CodeT5-base")
        self.SQL_TIMEOUT = int(os.getenv("SQL_TIMEOUT", "30"))
        self.SQL_MAX_RESULTS = int(os.getenv("SQL_MAX_RESULTS", "1000"))
        
        # Report Generation
        self.SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "google/pegasus-cnn_dailymail")
        self.REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))
        
        # Security
        self.SECRET_KEY = os.getenv("SECRET_KEY", "cctns-demo-secret-key-2024")
        self.API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Performance
        self.MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
        self.REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))
        
        # File Upload
        self.MAX_FILE_SIZE = os.getenv("MAX_FILE_SIZE", "50MB")
        self.ALLOWED_AUDIO_FORMATS = os.getenv("ALLOWED_AUDIO_FORMATS", "wav,mp3,m4a,ogg")
        
        # Initialize directories
        self._create_directories()
        
        # Load .env file if exists
        self._load_env_file()
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.MODELS_DIR,
            self.REPORTS_DIR,
            Path("logs"),
            Path("temp"),
            Path("uploads"),
            Path("web/static")
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not create directory {directory}: {e}")
    
    def _load_env_file(self):
        """Load .env file if it exists"""
        env_file = Path(".env")
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                logger.info("✅ Loaded .env file")
            except Exception as e:
                logger.warning(f"Could not load .env file: {e}")

# Create global settings instance
settings = Settings()