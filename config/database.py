"""
Database configuration and connection management for CCTNS Oracle database
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import cx_Oracle
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.pool import QueuePool
from .settings import settings

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    
    # Connection settings
    host: str = "localhost"
    port: int = 1521
    service_name: str = "CCTNS"
    username: str = ""
    password: str = ""
    
    # Pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # Query settings
    query_timeout: int = 30
    max_results: int = 1000
    
    # Security settings
    enable_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables"""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "1521")),
            service_name=os.getenv("DB_SERVICE_NAME", "CCTNS"),
            username=os.getenv("DB_USERNAME", ""),
            password=os.getenv("DB_PASSWORD", ""),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            query_timeout=int(os.getenv("DB_QUERY_TIMEOUT", "30")),
            max_results=int(os.getenv("DB_MAX_RESULTS", "1000")),
            enable_ssl=os.getenv("DB_ENABLE_SSL", "false").lower() == "true",
            ssl_cert_path=os.getenv("DB_SSL_CERT_PATH")
        )
    
    @property
    def connection_string(self) -> str:
        """Generate Oracle connection string"""
        if settings.ORACLE_CONNECTION_STRING:
            return settings.ORACLE_CONNECTION_STRING
        
        if self.enable_ssl:
            protocol = "tcps"
        else:
            protocol = "tcp"
            
        dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL={protocol})(HOST={self.host})(PORT={self.port}))(CONNECT_DATA=(SERVICE_NAME={self.service_name})))"
        return f"oracle+cx_oracle://{self.username}:{self.password}@{dsn}"
    
    def create_engine(self):
        """Create SQLAlchemy engine with proper configuration"""
        engine_args = {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "poolclass": QueuePool,
            "echo": settings.DEBUG
        }
        
        return create_engine(self.connection_string, **engine_args)

class DatabaseManager:
    """Database connection and schema management"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig.from_env()
        self.engine = None
        self.metadata = None
        self._schema_cache = {}
        
    def initialize(self):
        """Initialize database connection and load schema metadata"""
        try:
            self.engine = self.config.create_engine()
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute("SELECT 1 FROM DUAL")
                logger.info("Database connection established successfully")
            
            # Load metadata
            self.metadata = MetaData()
            self.metadata.reflect(bind=self.engine)
            
            # Cache table information
            self._load_schema_cache()
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _load_schema_cache(self):
        """Load and cache database schema information"""
        try:
            inspector = inspect(self.engine)
            
            # Cache table names and columns
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                
                self._schema_cache[table_name] = {
                    "columns": [col["name"] for col in columns],
                    "column_details": columns,
                    "foreign_keys": foreign_keys,
                    "primary_keys": inspector.get_pk_constraint(table_name)
                }
            
            logger.info(f"Schema cache loaded for {len(self._schema_cache)} tables")
            
        except Exception as e:
            logger.error(f"Schema cache loading failed: {e}")
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get cached table information"""
        return self._schema_cache.get(table_name.upper(), {})
    
    def get_all_tables(self) -> list:
        """Get list of all available tables"""
        return list(self._schema_cache.keys())
    
    def validate_query(self, sql: str) -> Dict[str, Any]:
        """Validate SQL query against schema"""
        # TODO: Implement SQL validation logic
        # This should check for:
        # - Valid table names
        # - Valid column names
        # - Proper JOIN relationships
        # - Security constraints (no DROP, DELETE, etc.)
        
        return {
            "valid": True,
            "warnings": [],
            "errors": []
        }
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# CCTNS-specific schema constants
CCTNS_TABLES = {
    "DISTRICT_MASTER": {
        "type": "master",
        "description": "Master table for district information"
    },
    "STATION_MASTER": {
        "type": "master", 
        "description": "Master table for police station information"
    },
    "OFFICER_MASTER": {
        "type": "master",
        "description": "Master table for police officer information"
    },
    "CRIME_TYPE_MASTER": {
        "type": "master",
        "description": "Master table for crime type classifications"
    },
    "FIR": {
        "type": "transaction",
        "description": "First Information Report records"
    },
    "ARREST": {
        "type": "transaction", 
        "description": "Arrest records"
    }
}

# Global database manager instance
db_manager = DatabaseManager()