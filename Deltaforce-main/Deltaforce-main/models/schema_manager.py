"""
Schema Manager for CCTNS Copilot Engine
Manages database schema information and relationships
"""
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import inspect, MetaData, Table, Column, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

class SchemaManager:
    def __init__(self, connection_string: str, config: dict = None):
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string
        self.config = config or {}
        
        # Initialize database connection
        self.engine = sa.create_engine(connection_string)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.metadata = MetaData()
        
        # Schema information cache
        self.schema_cache = {
            "tables": {},
            "relationships": {},
            "indexes": {},
            "constraints": {},
            "last_updated": None
        }
        
        # CCTNS specific schema definitions
        self.cctns_schema = self._load_cctns_schema()
        
        # Load schema on initialization
        self._refresh_schema_cache()
    
    def _load_cctns_schema(self) -> Dict[str, Any]:
        """Load CCTNS database schema definition"""
        return {
            "tables": {
                "FIR": {
                    "description": "First Information Report - Primary crime reporting table",
                    "primary_key": "fir_id",
                    "columns": {
                        "fir_id": {"type": "NUMBER", "description": "Unique FIR identifier"},
                        "fir_number": {"type": "VARCHAR2", "description": "FIR registration number"},
                        "district_id": {"type": "NUMBER", "description": "District where FIR was registered"},
                        "ps_id": {"type": "NUMBER", "description": "Police station ID"},
                        "crime_type_id": {"type": "NUMBER", "description": "Type of crime"},
                        "date_reported": {"type": "DATE", "description": "Date when FIR was reported"},
                        "date_occurred": {"type": "DATE", "description": "Date when incident occurred"},
                        "complainant_name": {"type": "VARCHAR2", "description": "Name of complainant"},
                        "complainant_contact": {"type": "VARCHAR2", "description": "Contact details"},
                        "incident_location": {"type": "VARCHAR2", "description": "Location of incident"},
                        "description": {"type": "CLOB", "description": "Detailed description of incident"},
                        "status": {"type": "VARCHAR2", "description": "Current status of FIR"},
                        "investigating_officer_id": {"type": "NUMBER", "description": "Assigned investigating officer"},
                        "created_by": {"type": "NUMBER", "description": "Officer who created FIR"},
                        "created_date": {"type": "DATE", "description": "Creation timestamp"}
                    },
                    "relationships": {
                        "district_id": "DISTRICT_MASTER.district_id",
                        "ps_id": "POLICE_STATION_MASTER.ps_id",
                        "crime_type_id": "CRIME_TYPE_MASTER.crime_type_id",
                        "investigating_officer_id": "OFFICER_MASTER.officer_id"
                    }
                },
                "DISTRICT_MASTER": {
                    "description": "Master table for districts",
                    "primary_key": "district_id",
                    "columns": {
                        "district_id": {"type": "NUMBER", "description": "Unique district identifier"},
                        "district_name": {"type": "VARCHAR2", "description": "District name"},
                        "district_code": {"type": "VARCHAR2", "description": "District code"},
                        "state_id": {"type": "NUMBER", "description": "State identifier"},
                        "headquarters": {"type": "VARCHAR2", "description": "District headquarters"},
                        "population": {"type": "NUMBER", "description": "District population"},
                        "area_sqkm": {"type": "NUMBER", "description": "Area in square kilometers"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    }
                },
                "POLICE_STATION_MASTER": {
                    "description": "Master table for police stations",
                    "primary_key": "ps_id",
                    "columns": {
                        "ps_id": {"type": "NUMBER", "description": "Unique police station identifier"},
                        "ps_name": {"type": "VARCHAR2", "description": "Police station name"},
                        "ps_code": {"type": "VARCHAR2", "description": "Police station code"},
                        "district_id": {"type": "NUMBER", "description": "District identifier"},
                        "address": {"type": "VARCHAR2", "description": "Police station address"},
                        "contact_number": {"type": "VARCHAR2", "description": "Contact number"},
                        "sho_id": {"type": "NUMBER", "description": "Station House Officer ID"},
                        "jurisdiction_area": {"type": "VARCHAR2", "description": "Jurisdiction area"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    },
                    "relationships": {
                        "district_id": "DISTRICT_MASTER.district_id",
                        "sho_id": "OFFICER_MASTER.officer_id"
                    }
                },
                "OFFICER_MASTER": {
                    "description": "Master table for police officers",
                    "primary_key": "officer_id",
                    "columns": {
                        "officer_id": {"type": "NUMBER", "description": "Unique officer identifier"},
                        "officer_name": {"type": "VARCHAR2", "description": "Officer full name"},
                        "badge_number": {"type": "VARCHAR2", "description": "Badge/service number"},
                        "rank": {"type": "VARCHAR2", "description": "Officer rank"},
                        "designation": {"type": "VARCHAR2", "description": "Current designation"},
                        "district_id": {"type": "NUMBER", "description": "Current district posting"},
                        "ps_id": {"type": "NUMBER", "description": "Current police station"},
                        "contact_number": {"type": "VARCHAR2", "description": "Contact number"},
                        "email": {"type": "VARCHAR2", "description": "Email address"},
                        "date_joined": {"type": "DATE", "description": "Date of joining service"},
                        "status": {"type": "VARCHAR2", "description": "Current status (Active/Inactive)"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    },
                    "relationships": {
                        "district_id": "DISTRICT_MASTER.district_id",
                        "ps_id": "POLICE_STATION_MASTER.ps_id"
                    }
                },
                "CRIME_TYPE_MASTER": {
                    "description": "Master table for crime types",
                    "primary_key": "crime_type_id",
                    "columns": {
                        "crime_type_id": {"type": "NUMBER", "description": "Unique crime type identifier"},
                        "crime_type_code": {"type": "VARCHAR2", "description": "Crime type code"},
                        "description": {"type": "VARCHAR2", "description": "Crime type description"},
                        "ipc_section": {"type": "VARCHAR2", "description": "Relevant IPC section"},
                        "category": {"type": "VARCHAR2", "description": "Crime category"},
                        "severity": {"type": "VARCHAR2", "description": "Crime severity level"},
                        "is_cognizable": {"type": "CHAR", "description": "Is cognizable offense (Y/N)"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    }
                },
                "ARREST": {
                    "description": "Arrest records table",
                    "primary_key": "arrest_id",
                    "columns": {
                        "arrest_id": {"type": "NUMBER", "description": "Unique arrest identifier"},
                        "fir_id": {"type": "NUMBER", "description": "Related FIR ID"},
                        "accused_name": {"type": "VARCHAR2", "description": "Name of accused"},
                        "accused_address": {"type": "VARCHAR2", "description": "Address of accused"},
                        "age": {"type": "NUMBER", "description": "Age of accused"},
                        "gender": {"type": "CHAR", "description": "Gender (M/F/O)"},
                        "arrest_date": {"type": "DATE", "description": "Date of arrest"},
                        "arrest_location": {"type": "VARCHAR2", "description": "Location of arrest"},
                        "arresting_officer_id": {"type": "NUMBER", "description": "Arresting officer ID"},
                        "charges": {"type": "VARCHAR2", "description": "Charges against accused"},
                        "custody_status": {"type": "VARCHAR2", "description": "Current custody status"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    },
                    "relationships": {
                        "fir_id": "FIR.fir_id",
                        "arresting_officer_id": "OFFICER_MASTER.officer_id"
                    }
                },
                "INVESTIGATION": {
                    "description": "Investigation progress tracking",
                    "primary_key": "investigation_id",
                    "columns": {
                        "investigation_id": {"type": "NUMBER", "description": "Unique investigation identifier"},
                        "fir_id": {"type": "NUMBER", "description": "Related FIR ID"},
                        "investigating_officer_id": {"type": "NUMBER", "description": "Investigating officer"},
                        "investigation_date": {"type": "DATE", "description": "Investigation date"},
                        "investigation_type": {"type": "VARCHAR2", "description": "Type of investigation"},
                        "location": {"type": "VARCHAR2", "description": "Investigation location"},
                        "findings": {"type": "CLOB", "description": "Investigation findings"},
                        "status": {"type": "VARCHAR2", "description": "Investigation status"},
                        "next_action": {"type": "VARCHAR2", "description": "Next planned action"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    },
                    "relationships": {
                        "fir_id": "FIR.fir_id",
                        "investigating_officer_id": "OFFICER_MASTER.officer_id"
                    }
                },
                "EVIDENCE": {
                    "description": "Evidence collection and tracking",
                    "primary_key": "evidence_id",
                    "columns": {
                        "evidence_id": {"type": "NUMBER", "description": "Unique evidence identifier"},
                        "fir_id": {"type": "NUMBER", "description": "Related FIR ID"},
                        "evidence_type": {"type": "VARCHAR2", "description": "Type of evidence"},
                        "description": {"type": "VARCHAR2", "description": "Evidence description"},
                        "collection_date": {"type": "DATE", "description": "Date collected"},
                        "collection_location": {"type": "VARCHAR2", "description": "Collection location"},
                        "collected_by": {"type": "NUMBER", "description": "Officer who collected"},
                        "chain_of_custody": {"type": "CLOB", "description": "Chain of custody log"},
                        "storage_location": {"type": "VARCHAR2", "description": "Current storage location"},
                        "status": {"type": "VARCHAR2", "description": "Evidence status"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    },
                    "relationships": {
                        "fir_id": "FIR.fir_id",
                        "collected_by": "OFFICER_MASTER.officer_id"
                    }
                },
                "COURT_CASE": {
                    "description": "Court case proceedings",
                    "primary_key": "case_id",
                    "columns": {
                        "case_id": {"type": "NUMBER", "description": "Unique case identifier"},
                        "fir_id": {"type": "NUMBER", "description": "Related FIR ID"},
                        "court_name": {"type": "VARCHAR2", "description": "Court name"},
                        "case_number": {"type": "VARCHAR2", "description": "Court case number"},
                        "case_type": {"type": "VARCHAR2", "description": "Type of case"},
                        "filing_date": {"type": "DATE", "description": "Case filing date"},
                        "hearing_date": {"type": "DATE", "description": "Next hearing date"},
                        "case_status": {"type": "VARCHAR2", "description": "Current case status"},
                        "prosecutor": {"type": "VARCHAR2", "description": "Prosecutor name"},
                        "defense_lawyer": {"type": "VARCHAR2", "description": "Defense lawyer"},
                        "judge_name": {"type": "VARCHAR2", "description": "Presiding judge"},
                        "verdict": {"type": "VARCHAR2", "description": "Court verdict"},
                        "sentence": {"type": "VARCHAR2", "description": "Sentence if convicted"},
                        "created_date": {"type": "DATE", "description": "Record creation date"}
                    },
                    "relationships": {
                        "fir_id": "FIR.fir_id"
                    }
                }
            },
            "views": {
                "VW_CRIME_SUMMARY": {
                    "description": "Crime summary view with district and officer details",
                    "base_tables": ["FIR", "DISTRICT_MASTER", "CRIME_TYPE_MASTER", "OFFICER_MASTER"]
                },
                "VW_OFFICER_PERFORMANCE": {
                    "description": "Officer performance metrics view",
                    "base_tables": ["OFFICER_MASTER", "FIR", "ARREST", "INVESTIGATION"]
                }
            }
        }
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _refresh_schema_cache(self):
        """Refresh schema information cache from database"""
        try:
            with self.get_session() as session:
                inspector = inspect(self.engine)
                
                # Get table information
                self.schema_cache["tables"] = {}
                for table_name in inspector.get_table_names():
                    table_info = self._get_table_metadata(inspector, table_name)
                    self.schema_cache["tables"][table_name] = table_info
                
                # Get relationships
                self.schema_cache["relationships"] = self._get_table_relationships(inspector)
                
                # Get indexes
                self.schema_cache["indexes"] = self._get_table_indexes(inspector)
                
                # Get constraints
                self.schema_cache["constraints"] = self._get_table_constraints(inspector)
                
                self.schema_cache["last_updated"] = datetime.now()
                
                self.logger.info(f"Schema cache refreshed. Found {len(self.schema_cache['tables'])} tables")
                
        except Exception as e:
            self.logger.error(f"Failed to refresh schema cache: {e}")
    
    def _get_table_metadata(self, inspector, table_name: str) -> Dict[str, Any]:
        """Get detailed metadata for a specific table"""
        try:
            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            
            table_info = {
                "name": table_name,
                "columns": {},
                "primary_key": pk_constraint.get("constrained_columns", []),
                "description": self.cctns_schema["tables"].get(table_name, {}).get("description", ""),
                "row_count": self._get_table_row_count(table_name)
            }
            
            for col in columns:
                col_name = col["name"]
                cctns_col_info = (
                    self.cctns_schema["tables"]
                    .get(table_name, {})
                    .get("columns", {})
                    .get(col_name, {})
                )
                
                table_info["columns"][col_name] = {
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": col.get("default"),
                    "description": cctns_col_info.get("description", ""),
                    "autoincrement": col.get("autoincrement", False)
                }
            
            return table_info
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata for table {table_name}: {e}")
            return {}
    
    def _get_table_relationships(self, inspector) -> Dict[str, List[Dict[str, Any]]]:
        """Get foreign key relationships between tables"""
        relationships = {}
        
        try:
            for table_name in inspector.get_table_names():
                fk_constraints = inspector.get_foreign_keys(table_name)
                table_relationships = []
                
                for fk in fk_constraints:
                    relationship = {
                        "constraint_name": fk["name"],
                        "local_columns": fk["constrained_columns"],
                        "foreign_table": fk["referred_table"],
                        "foreign_columns": fk["referred_columns"],
                        "on_delete": fk.get("on_delete"),
                        "on_update": fk.get("on_update")
                    }
                    table_relationships.append(relationship)
                
                if table_relationships:
                    relationships[table_name] = table_relationships
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Failed to get table relationships: {e}")
            return {}
    
    def _get_table_indexes(self, inspector) -> Dict[str, List[Dict[str, Any]]]:
        """Get index information for all tables"""
        indexes = {}
        
        try:
            for table_name in inspector.get_table_names():
                table_indexes = inspector.get_indexes(table_name)
                if table_indexes:
                    indexes[table_name] = table_indexes
            
            return indexes
            
        except Exception as e:
            self.logger.error(f"Failed to get table indexes: {e}")
            return {}
    
    def _get_table_constraints(self, inspector) -> Dict[str, Dict[str, Any]]:
        """Get constraint information for all tables"""
        constraints = {}
        
        try:
            for table_name in inspector.get_table_names():
                table_constraints = {
                    "primary_key": inspector.get_pk_constraint(table_name),
                    "foreign_keys": inspector.get_foreign_keys(table_name),
                    "unique_constraints": inspector.get_unique_constraints(table_name),
                    "check_constraints": inspector.get_check_constraints(table_name)
                }
                constraints[table_name] = table_constraints
            
            return constraints
            
        except Exception as e:
            self.logger.error(f"Failed to get table constraints: {e}")
            return {}
    
    def _get_table_row_count(self, table_name: str) -> int:
        """Get approximate row count for a table"""
        try:
            with self.get_session() as session:
                # Use Oracle's num_rows from user_tables for better performance
                result = session.execute(text(
                    "SELECT num_rows FROM user_tables WHERE table_name = UPPER(:table_name)"
                ), {"table_name": table_name})
                
                row = result.fetchone()
                if row and row[0] is not None:
                    return row[0]
                
                # Fallback to actual count (slower)
                result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
                
        except Exception as e:
            self.logger.warning(f"Could not get row count for {table_name}: {e}")
            return 0
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive information about a specific table"""
        table_name_upper = table_name.upper()
        
        if table_name_upper not in self.schema_cache["tables"]:
            # Try to refresh cache if table not found
            self._refresh_schema_cache()
        
        if table_name_upper not in self.schema_cache["tables"]:
            return {"error": f"Table '{table_name}' not found"}
        
        table_info = self.schema_cache["tables"][table_name_upper].copy()
        
        # Add relationship information
        table_info["relationships"] = self.schema_cache["relationships"].get(table_name_upper, [])
        
        # Add index information
        table_info["indexes"] = self.schema_cache["indexes"].get(table_name_upper, [])
        
        # Add constraint information
        table_info["constraints"] = self.schema_cache["constraints"].get(table_name_upper, {})
        
        # Add CCTNS-specific information
        cctns_info = self.cctns_schema["tables"].get(table_name_upper, {})
        if cctns_info:
            table_info["cctns_description"] = cctns_info.get("description", "")
            table_info["cctns_relationships"] = cctns_info.get("relationships", {})
        
        return table_info
    
    def get_all_tables(self) -> List[str]:
        """Get list of all available tables"""
        return list(self.schema_cache["tables"].keys())
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a specific table"""
        table_info = self.get_table_info(table_name)
        
        if "error" in table_info:
            return []
        
        columns = []
        for col_name, col_info in table_info["columns"].items():
            columns.append({
                "name": col_name,
                "type": col_info["type"],
                "nullable": col_info["nullable"],
                "description": col_info["description"],
                "is_primary_key": col_name in table_info["primary_key"]
            })
        
        return columns
    
    def get_related_tables(self, table_name: str) -> Dict[str, List[str]]:
        """Get tables related to the specified table"""
        table_name_upper = table_name.upper()
        
        # Tables this table references (via foreign keys)
        references = []
        relationships = self.schema_cache["relationships"].get(table_name_upper, [])
        for rel in relationships:
            references.append(rel["foreign_table"])
        
        # Tables that reference this table
        referenced_by = []
        for table, rels in self.schema_cache["relationships"].items():
            for rel in rels:
                if rel["foreign_table"] == table_name_upper:
                    referenced_by.append(table)
        
        return {
            "references": references,
            "referenced_by": referenced_by
        }
    
    def suggest_joins(self, tables: List[str]) -> List[Dict[str, Any]]:
        """Suggest possible joins between multiple tables"""
        suggestions = []
        
        for i, table1 in enumerate(tables):
            for table2 in tables[i+1:]:
                join_info = self._find_join_path(table1.upper(), table2.upper())
                if join_info:
                    suggestions.append(join_info)
        
        return suggestions
    
    def _find_join_path(self, table1: str, table2: str) -> Optional[Dict[str, Any]]:
        """Find join path between two tables"""
        # Direct relationship
        table1_rels = self.schema_cache["relationships"].get(table1, [])
        for rel in table1_rels:
            if rel["foreign_table"] == table2:
                return {
                    "type": "direct",
                    "table1": table1,
                    "table2": table2,
                    "join_condition": f"{table1}.{rel['local_columns'][0]} = {table2}.{rel['foreign_columns'][0]}"
                }
        
        # Reverse relationship
        table2_rels = self.schema_cache["relationships"].get(table2, [])
        for rel in table2_rels:
            if rel["foreign_table"] == table1:
                return {
                    "type": "direct",
                    "table1": table1,
                    "table2": table2,
                    "join_condition": f"{table1}.{rel['foreign_columns'][0]} = {table2}.{rel['local_columns'][0]}"
                }
        
        # Could implement indirect joins through intermediate tables here
        return None
    
    def validate_query_tables(self, tables: List[str]) -> Dict[str, Any]:
        """Validate that specified tables exist and are accessible"""
        validation = {
            "valid": True,
            "existing_tables": [],
            "missing_tables": [],
            "warnings": []
        }
        
        for table in tables:
            table_upper = table.upper()
            if table_upper in self.schema_cache["tables"]:
                validation["existing_tables"].append(table_upper)
            else:
                validation["missing_tables"].append(table)
                validation["valid"] = False
        
        # Check for potential issues
        if len(validation["existing_tables"]) > 5:
            validation["warnings"].append("Query involves many tables - consider performance impact")
        
        return validation
    
    def get_column_suggestions(self, partial_name: str, table_name: Optional[str] = None) -> List[str]:
        """Get column name suggestions based on partial input"""
        suggestions = []
        partial_lower = partial_name.lower()
        
        if table_name:
            # Search in specific table
            table_info = self.get_table_info(table_name)
            if "columns" in table_info:
                for col_name in table_info["columns"]:
                    if partial_lower in col_name.lower():
                        suggestions.append(f"{table_name}.{col_name}")
        else:
            # Search across all tables
            for table, table_info in self.schema_cache["tables"].items():
                for col_name in table_info["columns"]:
                    if partial_lower in col_name.lower():
                        suggestions.append(f"{table}.{col_name}")
        
        return sorted(suggestions)[:10]  # Limit to 10 suggestions
    
    def get_schema_summary(self) -> Dict[str, Any]:
        """Get summary of the entire schema"""
        total_tables = len(self.schema_cache["tables"])
        total_columns = sum(len(table["columns"]) for table in self.schema_cache["tables"].values())
        total_relationships = sum(len(rels) for rels in self.schema_cache["relationships"].values())
        
        # Table size distribution
        table_sizes = {}
        for table_name, table_info in self.schema_cache["tables"].items():
            row_count = table_info.get("row_count", 0)
            if row_count > 1000000:
                size_category = "large"
            elif row_count > 10000:
                size_category = "medium"
            elif row_count > 0:
                size_category = "small"
            else:
                size_category = "empty"
            
            table_sizes[size_category] = table_sizes.get(size_category, 0) + 1
        
        return {
            "total_tables": total_tables,
            "total_columns": total_columns,
            "total_relationships": total_relationships,
            "table_size_distribution": table_sizes,
            "last_updated": self.schema_cache["last_updated"],
            "core_tables": list(self.cctns_schema["tables"].keys()),
            "available_views": list(self.cctns_schema.get("views", {}).keys())
        }
    
    def refresh_schema(self):
        """Manually refresh schema cache"""
        self._refresh_schema_cache()
        return {
            "status": "success",
            "message": "Schema cache refreshed",
            "timestamp": self.schema_cache["last_updated"],
            "tables_found": len(self.schema_cache["tables"])
        }