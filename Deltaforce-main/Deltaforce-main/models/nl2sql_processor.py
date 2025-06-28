"""
Natural Language to SQL Processor
"""
import logging
import asyncio
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class NL2SQLProcessor:
    """Convert natural language queries to SQL"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.database_type = config.get("database_type", "sqlite")
        
        # Common query patterns and templates
        self.query_patterns = {
            r'\bhow many\b|\bcount\b': 'count',
            r'\bshow\b|\blist\b|\bdisplay\b': 'select',
            r'\btop\b|\bhighest\b|\bmost\b': 'top',
            r'\bcompare\b|\bcomparison\b': 'compare',
            r'\btrend\b|\bover time\b': 'trend'
        }
        
        # Entity mapping
        self.entity_mapping = {
            'fir': 'FIR',
            'firs': 'FIR',
            'arrest': 'ARREST',
            'arrests': 'ARREST',
            'officer': 'OFFICER_MASTER',
            'officers': 'OFFICER_MASTER',
            'district': 'DISTRICT_MASTER',
            'districts': 'DISTRICT_MASTER',
            'station': 'STATION_MASTER',
            'stations': 'STATION_MASTER',
            'crime': 'CRIME_TYPE_MASTER',
            'crimes': 'CRIME_TYPE_MASTER'
        }
        
        # District names
        self.districts = [
            'Guntur', 'Vijayawada', 'Visakhapatnam', 'Tirupati', 'Kurnool',
            'Nellore', 'Kadapa', 'Chittoor', 'Krishna', 'West Godavari',
            'East Godavari', 'Srikakulam', 'Vizianagaram', 'Anantapur', 'Prakasam'
        ]
        
        logger.info("🔍 NL2SQLProcessor initialized")
        logger.info(f"Database type: {self.database_type}")
    
    async def generate_sql(self, text: str) -> Dict[str, Any]:
        """
        Generate SQL query from natural language text
        
        Args:
            text: Natural language query
            
        Returns:
            Dictionary with SQL query and metadata
        """
        try:
            logger.info(f"🔍 Processing query: {text}")
            
            # Clean and normalize text
            normalized_text = self._normalize_text(text)
            
            # Detect query type
            query_type = self._detect_query_type(normalized_text)
            
            # Extract entities
            entities = self._extract_entities(normalized_text)
            
            # Generate SQL based on pattern
            sql_query = await self._generate_sql_by_pattern(query_type, entities, normalized_text)
            
            # Validate SQL
            is_valid = self._validate_sql(sql_query)
            
            result = {
                "sql": sql_query,
                "valid": is_valid,
                "confidence": 0.8 if is_valid else 0.3,
                "query_type": query_type,
                "entities": entities,
                "original_text": text,
                "normalized_text": normalized_text
            }
            
            if is_valid:
                logger.info(f"✅ Generated SQL: {sql_query}")
            else:
                logger.warning(f"⚠️ Invalid SQL generated: {sql_query}")
                result["error"] = "Generated SQL failed validation"
            
            return result
            
        except Exception as e:
            logger.error(f"❌ SQL generation failed: {e}")
            return {
                "sql": "",
                "valid": False,
                "confidence": 0.0,
                "error": str(e),
                "original_text": text
            }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize input text"""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Replace common abbreviations
        replacements = {
            'fir': 'FIR',
            'sho': 'station house officer',
            'asi': 'assistant sub inspector',
            'si': 'sub inspector'
        }
        
        for abbr, full in replacements.items():
            text = re.sub(rf'\b{abbr}\b', full, text)
        
        return text
    
    def _detect_query_type(self, text: str) -> str:
        """Detect the type of query"""
        for pattern, query_type in self.query_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return query_type
        return 'select'  # default
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text"""
        entities = {
            'tables': [],
            'districts': [],
            'dates': [],
            'numbers': []
        }
        
        # Extract table entities
        for entity, table in self.entity_mapping.items():
            if entity in text:
                if table not in entities['tables']:
                    entities['tables'].append(table)
        
        # Extract district names
        for district in self.districts:
            if district.lower() in text:
                entities['districts'].append(district)
        
        # Extract numbers
        numbers = re.findall(r'\d+', text)
        entities['numbers'] = numbers
        
        # Extract date-related terms
        date_terms = re.findall(r'\b(today|yesterday|this month|last month|this year|last year)\b', text)
        entities['dates'] = date_terms
        
        return entities
    
    async def _generate_sql_by_pattern(self, query_type: str, entities: Dict, text: str) -> str:
        """Generate SQL based on detected pattern"""
        
        # Default table if none detected
        main_table = entities['tables'][0] if entities['tables'] else 'FIR'
        
        if query_type == 'count':
            sql = f"SELECT COUNT(*) as total_count FROM {main_table}"
            
        elif query_type == 'select':
            if main_table == 'FIR':
                sql = f"SELECT fir_id, fir_number, incident_date, status FROM {main_table}"
            elif main_table == 'ARREST':
                sql = f"SELECT arrest_id, arrested_person_name, arrest_date FROM {main_table}"
            elif main_table == 'OFFICER_MASTER':
                sql = f"SELECT officer_id, officer_name, rank FROM {main_table}"
            else:
                sql = f"SELECT * FROM {main_table}"
                
        elif query_type == 'top':
            if 'officer' in text:
                sql = """
                SELECT o.officer_name, COUNT(a.arrest_id) as arrest_count 
                FROM OFFICER_MASTER o 
                LEFT JOIN ARREST a ON o.officer_id = a.officer_id 
                GROUP BY o.officer_name 
                ORDER BY arrest_count DESC
                """
            else:
                sql = f"SELECT * FROM {main_table} ORDER BY incident_date DESC"
                
        elif query_type == 'compare':
            if entities['districts'] and len(entities['districts']) >= 2:
                district1, district2 = entities['districts'][:2]
                sql = f"""
                SELECT d.district_name, COUNT(f.fir_id) as fir_count
                FROM DISTRICT_MASTER d
                LEFT JOIN FIR f ON d.district_id = f.district_id
                WHERE d.district_name IN ('{district1}', '{district2}')
                GROUP BY d.district_name
                """
            else:
                sql = f"SELECT * FROM {main_table}"
                
        else:
            sql = f"SELECT * FROM {main_table}"
        
        # Add district filter if specified
        if entities['districts'] and 'WHERE' not in sql.upper():
            district = entities['districts'][0]
            if main_table == 'FIR':
                sql += f" WHERE district_id = (SELECT district_id FROM DISTRICT_MASTER WHERE district_name = '{district}')"
        
        # Add LIMIT
        sql += " LIMIT 100"
        
        return sql.strip()
    
    def _validate_sql(self, sql: str) -> bool:
        """Basic SQL validation"""
        if not sql or not sql.strip():
            return False
        
        # Check for dangerous keywords
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER']
        sql_upper = sql.upper()
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        
        # Check if it starts with SELECT
        if not sql_upper.strip().startswith('SELECT'):
            return False
        
        return True
    
    def get_sample_queries(self) -> List[str]:
        """Get sample queries for testing"""
        return [
            "How many FIRs were registered in Guntur district?",
            "Show me recent arrests",
            "List officers in Visakhapatnam district",
            "Count total crimes this month",
            "Show top performing officers",
            "Compare crime rates in Guntur and Krishna districts"
        ]