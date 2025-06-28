"""
SQL Executor with database connectivity
"""
import logging
import asyncio
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SQLExecutor:
    """Execute SQL queries against the database"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.db_type = self._detect_db_type(connection_string)
        
        logger.info(f"⚡ SQLExecutor initializing for {self.db_type}")
        logger.info(f"Connection: {connection_string}")
        
        # Initialize sample database if using SQLite
        if self.db_type == "sqlite":
            self._init_sample_database()
        
        # Test connection
        try:
            self._test_connection()
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
    
    def _detect_db_type(self, connection_string: str) -> str:
        """Detect database type from connection string"""
        if connection_string.startswith("sqlite"):
            return "sqlite"
        elif connection_string.startswith("oracle"):
            return "oracle"
        elif connection_string.startswith("postgresql"):
            return "postgresql"
        else:
            return "unknown"
    
    def _test_connection(self):
        """Test database connection with appropriate syntax"""
        try:
            if self.db_type == "sqlite":
                # Use SQLite syntax
                db_path = self.connection_string.replace("sqlite:///", "").replace("sqlite://", "")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")  # SQLite doesn't need DUAL table
                cursor.fetchone()
                conn.close()
            elif self.db_type == "oracle":
                # Use Oracle syntax with DUAL
                # This would need Oracle connector
                pass
            else:
                logger.warning(f"Connection test not implemented for {self.db_type}")
        except Exception as e:
            raise Exception(f"Database connection test failed: {e}")
    
    def _init_sample_database(self):
        """Initialize SQLite database with sample CCTNS data"""
        try:
            # Extract database path from connection string
            db_path = self.connection_string.replace("sqlite:///", "").replace("sqlite://", "")
            
            logger.info(f"🗄️ Initializing sample database: {db_path}")
            
            # Check if database already exists and has data
            if Path(db_path).exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT COUNT(*) FROM FIR")
                    count = cursor.fetchone()[0]
                    if count > 0:
                        logger.info(f"📊 Database already exists with {count} FIR records")
                        conn.close()
                        return
                except sqlite3.OperationalError:
                    # Table doesn't exist, continue with initialization
                    pass
                conn.close()
            
            # Create database and tables
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create tables
            self._create_cctns_tables(cursor)
            
            # Insert sample data
            self._insert_sample_data(cursor)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Sample database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize sample database: {e}")
            raise
    
    def _create_cctns_tables(self, cursor):
        """Create CCTNS tables in SQLite"""
        
        logger.info("📋 Creating CCTNS tables...")
        
        # District Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DISTRICT_MASTER (
                district_id INTEGER PRIMARY KEY,
                district_code TEXT UNIQUE,
                district_name TEXT NOT NULL,
                state_code TEXT DEFAULT 'AP',
                created_date DATE DEFAULT CURRENT_DATE
            )
        """)
        
        # Station Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS STATION_MASTER (
                station_id INTEGER PRIMARY KEY,
                station_name TEXT NOT NULL,
                station_code TEXT UNIQUE,
                district_id INTEGER,
                latitude REAL,
                longitude REAL,
                contact_number TEXT,
                officer_in_charge TEXT,
                FOREIGN KEY (district_id) REFERENCES DISTRICT_MASTER(district_id)
            )
        """)
        
        # Officer Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS OFFICER_MASTER (
                officer_id INTEGER PRIMARY KEY,
                officer_name TEXT NOT NULL,
                rank TEXT,
                badge_number TEXT UNIQUE,
                station_id INTEGER,
                mobile_number TEXT,
                email TEXT,
                joining_date DATE,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (station_id) REFERENCES STATION_MASTER(station_id)
            )
        """)
        
        # Crime Type Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CRIME_TYPE_MASTER (
                crime_type_id INTEGER PRIMARY KEY,
                crime_code TEXT UNIQUE,
                crime_description TEXT NOT NULL,
                ipc_section TEXT,
                severity_level TEXT,
                category TEXT,
                sub_category TEXT
            )
        """)
        
        # FIR Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FIR (
                fir_id INTEGER PRIMARY KEY,
                fir_number TEXT UNIQUE NOT NULL,
                district_id INTEGER,
                station_id INTEGER,
                crime_type_id INTEGER,
                incident_date DATE NOT NULL,
                report_date DATE DEFAULT CURRENT_DATE,
                status TEXT DEFAULT 'OPEN',
                complainant_name TEXT,
                complainant_mobile TEXT,
                incident_location TEXT,
                description TEXT,
                investigating_officer_id INTEGER,
                FOREIGN KEY (district_id) REFERENCES DISTRICT_MASTER(district_id),
                FOREIGN KEY (station_id) REFERENCES STATION_MASTER(station_id),
                FOREIGN KEY (crime_type_id) REFERENCES CRIME_TYPE_MASTER(crime_type_id),
                FOREIGN KEY (investigating_officer_id) REFERENCES OFFICER_MASTER(officer_id)
            )
        """)
        
        # Arrest Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ARREST (
                arrest_id INTEGER PRIMARY KEY,
                fir_id INTEGER,
                officer_id INTEGER,
                arrested_person_name TEXT NOT NULL,
                arrested_person_age INTEGER,
                arrested_person_address TEXT,
                arrest_date DATE DEFAULT CURRENT_DATE,
                arrest_location TEXT,
                arrest_reason TEXT,
                bail_status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (fir_id) REFERENCES FIR(fir_id),
                FOREIGN KEY (officer_id) REFERENCES OFFICER_MASTER(officer_id)
            )
        """)
        
        logger.info("✅ Created all CCTNS tables")
    
    def _insert_sample_data(self, cursor):
        """Insert sample data into CCTNS tables"""
        
        logger.info("📊 Inserting sample data...")
        
        # Sample Districts
        districts = [
            (1, 'GNT', 'Guntur'),
            (2, 'VJA', 'Vijayawada'),
            (3, 'VSP', 'Visakhapatnam'),
            (4, 'TPT', 'Tirupati'),
            (5, 'KNL', 'Kurnool')
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO DISTRICT_MASTER (district_id, district_code, district_name) VALUES (?, ?, ?)",
            districts
        )
        
        # Sample Stations
        stations = [
            (1, 'Guntur Town Police Station', 'GNT001', 1, 16.3067, 80.4365, '9876543210', 'SI Ramesh'),
            (2, 'Vijayawada Central Police Station', 'VJA001', 2, 16.5062, 80.6480, '9876543211', 'CI Suresh'),
            (3, 'Visakhapatnam Port Police Station', 'VSP001', 3, 17.6868, 83.2185, '9876543212', 'SI Mahesh'),
            (4, 'Tirupati East Police Station', 'TPT001', 4, 13.6288, 79.4192, '9876543213', 'ASI Ganesh'),
            (5, 'Kurnool City Police Station', 'KNL001', 5, 15.8281, 78.0373, '9876543214', 'SI Rajesh')
        ]
        
        cursor.executemany(
            """INSERT OR IGNORE INTO STATION_MASTER 
               (station_id, station_name, station_code, district_id, latitude, longitude, contact_number, officer_in_charge) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            stations
        )
        
        # Sample Officers
        officers = [
            (1, 'Ramesh Kumar', 'SI', 'SI001', 1, '9988776655', 'ramesh@ap.gov.in', '2020-01-15'),
            (2, 'Suresh Reddy', 'CI', 'CI001', 2, '9988776656', 'suresh@ap.gov.in', '2018-03-20'),
            (3, 'Mahesh Babu', 'SI', 'SI002', 3, '9988776657', 'mahesh@ap.gov.in', '2019-07-10'),
            (4, 'Ganesh Rao', 'ASI', 'ASI001', 4, '9988776658', 'ganesh@ap.gov.in', '2021-02-28'),
            (5, 'Rajesh Varma', 'SI', 'SI003', 5, '9988776659', 'rajesh@ap.gov.in', '2020-11-05'),
            (6, 'Priya Sharma', 'ASI', 'ASI002', 1, '9988776660', 'priya@ap.gov.in', '2022-01-10'),
            (7, 'Vijay Krishna', 'HC', 'HC001', 2, '9988776661', 'vijay@ap.gov.in', '2019-09-15'),
            (8, 'Lakshmi Devi', 'SI', 'SI004', 3, '9988776662', 'lakshmi@ap.gov.in', '2021-06-20')
        ]
        
        cursor.executemany(
            """INSERT OR IGNORE INTO OFFICER_MASTER 
               (officer_id, officer_name, rank, badge_number, station_id, mobile_number, email, joining_date) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            officers
        )
        
        # Sample Crime Types
        crime_types = [
            (1, 'MUR', 'Murder', 'IPC 302', 'HIGH', 'Violent Crime', 'Homicide'),
            (2, 'THF', 'Theft', 'IPC 378', 'MEDIUM', 'Property Crime', 'Stealing'),
            (3, 'ROB', 'Robbery', 'IPC 392', 'HIGH', 'Property Crime', 'Armed Theft'),
            (4, 'AST', 'Assault', 'IPC 322', 'MEDIUM', 'Violent Crime', 'Physical Attack'),
            (5, 'FRD', 'Fraud', 'IPC 420', 'MEDIUM', 'Economic Crime', 'Cheating'),
            (6, 'KID', 'Kidnapping', 'IPC 363', 'HIGH', 'Violent Crime', 'Abduction'),
            (7, 'DVL', 'Domestic Violence', 'IPC 498A', 'MEDIUM', 'Domestic Crime', 'Family Violence'),
            (8, 'CYB', 'Cybercrime', 'IT Act 66', 'MEDIUM', 'Cyber Crime', 'Online Fraud')
        ]
        
        cursor.executemany(
            """INSERT OR IGNORE INTO CRIME_TYPE_MASTER 
               (crime_type_id, crime_code, crime_description, ipc_section, severity_level, category, sub_category) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            crime_types
        )
        
        # Sample FIRs
        firs = [
            (1, 'FIR001/2024', 1, 1, 2, '2024-01-15', '2024-01-15', 'OPEN', 'Raj Kumar', '9876543001', 'Guntur Market', 'Mobile phone theft case', 1),
            (2, 'FIR002/2024', 2, 2, 5, '2024-01-20', '2024-01-20', 'UNDER_INVESTIGATION', 'Sita Devi', '9876543002', 'Vijayawada Bus Stand', 'Online fraud case', 2),
            (3, 'FIR003/2024', 3, 3, 3, '2024-01-25', '2024-01-25', 'CLOSED', 'Mohan Rao', '9876543003', 'Visakhapatnam Port', 'Armed robbery case', 3),
            (4, 'FIR004/2024', 1, 1, 4, '2024-02-01', '2024-02-01', 'OPEN', 'Lakshmi Reddy', '9876543004', 'Guntur College', 'Assault case', 6),
            (5, 'FIR005/2024', 4, 4, 7, '2024-02-05', '2024-02-05', 'UNDER_INVESTIGATION', 'Kavitha Sharma', '9876543005', 'Tirupati Temple Area', 'Domestic violence case', 4),
            (6, 'FIR006/2024', 5, 5, 1, '2024-02-10', '2024-02-10', 'OPEN', 'Ramesh Babu', '9876543006', 'Kurnool Highway', 'Murder case', 5),
            (7, 'FIR007/2024', 2, 2, 8, '2024-02-12', '2024-02-12', 'UNDER_INVESTIGATION', 'Pradeep Kumar', '9876543007', 'Vijayawada IT Park', 'Cybercrime case', 7),
            (8, 'FIR008/2024', 3, 3, 2, '2024-02-15', '2024-02-15', 'CLOSED', 'Geetha Rani', '9876543008', 'Visakhapatnam Beach', 'Purse theft case', 8),
            (9, 'FIR009/2024', 1, 1, 6, '2024-02-18', '2024-02-18', 'OPEN', 'Suresh Kumar', '9876543009', 'Guntur Railway Station', 'Kidnapping case', 1),
            (10, 'FIR010/2024', 4, 4, 4, '2024-02-20', '2024-02-20', 'UNDER_INVESTIGATION', 'Anjali Devi', '9876543010', 'Tirupati Market', 'Assault case', 4),
            (11, 'FIR011/2024', 2, 2, 2, '2024-02-22', '2024-02-22', 'OPEN', 'Krishna Murthy', '9876543011', 'Vijayawada Railway Station', 'Wallet theft case', 7),
            (12, 'FIR012/2024', 5, 5, 5, '2024-02-25', '2024-02-25', 'CLOSED', 'Padmavathi', '9876543012', 'Kurnool Market', 'Credit card fraud case', 5)
        ]
        
        cursor.executemany(
            """INSERT OR IGNORE INTO FIR 
               (fir_id, fir_number, district_id, station_id, crime_type_id, incident_date, report_date, status, 
                complainant_name, complainant_mobile, incident_location, description, investigating_officer_id) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            firs
        )
        
        # Sample Arrests
        arrests = [
            (1, 3, 3, 'Ravi Kumar', 25, 'Visakhapatnam Slums', '2024-01-26', 'Visakhapatnam Port', 'Armed robbery', 'GRANTED'),
            (2, 8, 8, 'Venkat Rao', 30, 'Visakhapatnam City', '2024-02-16', 'Visakhapatnam Beach', 'Theft', 'PENDING'),
            (3, 2, 2, 'Cyber Criminal X', 28, 'Unknown', '2024-01-22', 'Vijayawada', 'Online fraud', 'DENIED'),
            (4, 6, 5, 'Accused Person', 35, 'Kurnool Village', '2024-02-12', 'Kurnool Highway', 'Murder', 'PENDING'),
            (5, 9, 1, 'Kidnapper Y', 32, 'Guntur Outskirts', '2024-02-19', 'Guntur Railway Station', 'Kidnapping', 'DENIED'),
            (6, 12, 5, 'Fraud Suspect Z', 29, 'Kurnool City', '2024-02-26', 'Kurnool Market', 'Credit card fraud', 'GRANTED')
        ]
        
        cursor.executemany(
            """INSERT OR IGNORE INTO ARREST 
               (arrest_id, fir_id, officer_id, arrested_person_name, arrested_person_age, 
                arrested_person_address, arrest_date, arrest_location, arrest_reason, bail_status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            arrests
        )
        
        logger.info("✅ Inserted sample data into all tables")
    
    async def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        try:
            logger.info(f"🔍 Executing query: {sql[:100]}...")
            
            # Validate query
            if not self._validate_query(sql):
                return {
                    "success": False,
                    "error": "Query validation failed - only SELECT queries are allowed",
                    "data": []
                }
            
            if self.db_type == "sqlite":
                return await self._execute_sqlite_query(sql)
            else:
                return {
                    "success": False,
                    "error": f"Database type {self.db_type} not supported in demo mode",
                    "data": []
                }
                
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    async def _execute_sqlite_query(self, sql: str) -> Dict[str, Any]:
        """Execute query against SQLite database"""
        try:
            # Extract database path
            db_path = self.connection_string.replace("sqlite:///", "").replace("sqlite://", "")
            
            # Connect and execute
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            start_time = datetime.now()
            cursor.execute(sql)
            results = cursor.fetchall()
            end_time = datetime.now()
            
            # Convert to list of dictionaries
            data = [dict(row) for row in results]
            
            conn.close()
            
            execution_time = (end_time - start_time).total_seconds()
            
            result = {
                "success": True,
                "data": data,
                "row_count": len(data),
                "execution_time": execution_time,
                "message": f"Query executed successfully - {len(data)} rows returned"
            }
            
            logger.info(f"✅ Query executed: {len(data)} rows in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ SQLite query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def _validate_query(self, sql: str) -> bool:
        """Validate SQL query for security"""
        if not sql or not sql.strip():
            return False
        
        sql_upper = sql.upper().strip()
        
        # Only allow SELECT queries
        if not sql_upper.startswith('SELECT'):
            return False
        
        # Block dangerous keywords
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER', 'CREATE', 'EXEC']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        
        return True
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            if self.db_type == "sqlite":
                db_path = self.connection_string.replace("sqlite:///", "").replace("sqlite://", "")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get table information
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                schema_info = {}
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    schema_info[table] = {
                        "columns": [{"name": col[1], "type": col[2], "nullable": not col[3]} for col in columns]
                    }
                
                conn.close()
                
                return {
                    "success": True,
                    "database_type": self.db_type,
                    "tables": tables,
                    "schema": schema_info
                }
            else:
                return {
                    "success": False,
                    "error": f"Database info not available for {self.db_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_sample_data(self, table_name: str, limit: int = 5) -> Dict[str, Any]:
        """Get sample data from a table"""
        try:
            sql = f"SELECT * FROM {table_name} LIMIT {limit}"
            return await self.execute_query(sql)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    async def get_table_counts(self) -> Dict[str, Any]:
        """Get record counts for all tables"""
        try:
            if self.db_type == "sqlite":
                db_path = self.connection_string.replace("sqlite:///", "").replace("sqlite://", "")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                counts = {}
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    counts[table] = count
                
                conn.close()
                
                return {
                    "success": True,
                    "table_counts": counts,
                    "total_tables": len(tables)
                }
            else:
                return {
                    "success": False,
                    "error": f"Table counts not available for {self.db_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }