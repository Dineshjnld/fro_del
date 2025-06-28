#!/usr/bin/env python3
"""
CCTNS Copilot Engine - Application Runner
Simple runner script to start the FastAPI application
"""
import os
import sys
import uvicorn
from pathlib import Path

def main():
    """Main function to start the application"""
    
    print("🚀 Starting CCTNS Copilot Engine...")
    
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    # Set environment variables if not set
    if not os.getenv("PYTHONPATH"):
        os.environ["PYTHONPATH"] = str(current_dir)
    
    # Default configuration
    config = {
        "app": "api.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False,  # Set to True for development
        "log_level": "info"
    }
    
    # Override with environment variables if available
    config["host"] = os.getenv("HOST", config["host"])
    config["port"] = int(os.getenv("PORT", config["port"]))
    config["reload"] = os.getenv("DEBUG", "false").lower() == "true"
    config["log_level"] = os.getenv("LOG_LEVEL", config["log_level"]).lower()
    
    print(f"📍 Host: {config['host']}:{config['port']}")
    print(f"🔧 Debug mode: {config['reload']}")
    print(f"📊 Log level: {config['log_level']}")
    
    # Create necessary directories
    directories = ["logs", "temp", "reports", "config"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("📁 Created necessary directories")
    
    # Check if required files exist and create minimal ones if missing
    config_dir = Path("config")
    
    # Create minimal settings.py if it doesn't exist
    settings_file = config_dir / "settings.py"
    if not settings_file.exists():
        print("📄 Creating minimal settings.py...")
        with open(settings_file, "w") as f:
            f.write('''
"""Minimal settings for CCTNS Copilot Engine"""
class Settings:
    APP_NAME = "CCTNS Copilot Engine"
    VERSION = "1.0.0"
    DEBUG = False
    HOST = "0.0.0.0"
    PORT = 8000
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ORACLE_CONNECTION_STRING = "oracle://user:password@localhost:1521/xe"

settings = Settings()
''')
    
    # Create minimal models_config.yaml if it doesn't exist
    config_file = config_dir / "models_config.yaml"
    if not config_file.exists():
        print("📄 Creating minimal models_config.yaml...")
        with open(config_file, "w") as f:
            f.write('''
# Minimal CCTNS Configuration
models:
  speech_to_text:
    fallback_model: "whisper"
    confidence_threshold: 0.7
  
text_processing:
  enable_police_terms: true

cctns_schema:
  tables: []
''')
    
    # Create __init__.py files if missing
    init_files = [
        "api/__init__.py",
        "models/__init__.py",
        "config/__init__.py"
    ]
    
    for init_file in init_files:
        init_path = Path(init_file)
        init_path.parent.mkdir(exist_ok=True)
        if not init_path.exists():
            init_path.write_text("# Auto-generated __init__.py\n")
    
    print("✅ Setup completed")
    
    try:
        # Start the server
        print("🌐 Starting server...")
        uvicorn.run(
            config["app"],
            host=config["host"],
            port=config["port"],
            reload=config["reload"],
            log_level=config["log_level"]
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if port 8000 is already in use")
        print("2. Ensure all required dependencies are installed")
        print("3. Check the logs directory for detailed error information")
        sys.exit(1)

if __name__ == "__main__":
    main()