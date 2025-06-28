"""
Configuration package for CCTNS Copilot Engine
"""

from .settings import settings
from .database import DatabaseConfig

__all__ = ["settings", "DatabaseConfig"]

# Version info
__version__ = "1.0.0"
__author__ = "AI4APH Team"
__description__ = "Configuration module for CCTNS Copilot Engine"

# Configuration validation
def validate_config():
    """Validate essential configuration settings"""
    errors = []
    
    # Check database configuration
    if not settings.ORACLE_CONNECTION_STRING:
        errors.append("ORACLE_CONNECTION_STRING is not set")
    
    # Check model directories
    if not settings.MODELS_DIR.exists():
        try:
            settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create models directory: {e}")
    
    # Check reports directory
    if not settings.REPORTS_DIR.exists():
        try:
            settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create reports directory: {e}")
    
    if errors:
        raise RuntimeError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return True

# Auto-validate on import
try:
    validate_config()
except RuntimeError as e:
    import warnings
    warnings.warn(f"Configuration warning: {e}", UserWarning)