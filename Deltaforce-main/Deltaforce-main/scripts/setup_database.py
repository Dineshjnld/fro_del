"""
Setup CCTNS database schema and sample data
"""
import cx_Oracle
import os
import logging
from pathlib import Path

def setup_database():
    """Setup database with sample data"""
    connection_string = os.getenv("ORACLE_CONNECTION_STRING")
    if not connection_string:
        print("❌ ORACLE_CONNECTION_STRING not set")
        return
    
    try:
        conn = cx_Oracle.connect(connection_string)
        cursor = conn.cursor()
        
        print("📊 Setting up CCTNS database...")
        
        # Read and execute schema
        schema_file = Path("data/schemas/cctns_schema.sql")
        if schema_file.exists():
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            # Execute schema creation
            for statement in schema_sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)
        
        # Load sample data
        sample_file = Path("data/schemas/sample_data.sql")
        if sample_file.exists():
            with open(sample_file, 'r') as f:
                sample_sql = f.read()
            
            for statement in sample_sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)
        
        conn.commit()
        print("✅ Database setup completed!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    setup_database()