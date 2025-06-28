
import type { QueryResult } from '../types';

// Synthetic Data
const MOCK_CRIME_DATA = [
  { crime_type: 'Theft', district: 'Guntur', count: 120 },
  { crime_type: 'Assault', district: 'Guntur', count: 45 },
  { crime_type: 'Burglary', district: 'Guntur', count: 78 },
  { crime_type: 'Robbery', district: 'Guntur', count: 30 },
  { crime_type: 'Theft', district: 'Visakhapatnam', count: 150 },
  { crime_type: 'Assault', district: 'Visakhapatnam', count: 60 },
];

const MOCK_ARREST_DATA = [
    { officer_name: 'S. Kumar', arrest_date: '2025-05-15', fir_description: 'Theft of motorcycle' },
    { officer_name: 'S. Kumar', arrest_date: '2025-05-22', fir_description: 'Shop burglary on Main St.' },
    { officer_name: 'A. Reddy', arrest_date: '2025-06-01', fir_description: 'Assault case at market' },
    { officer_name: 'S. Kumar', arrest_date: '2025-06-10', fir_description: 'Chain snatching incident' },
];

const MOCK_FIR_TREND = [
    { month: '2024-07', station: 'Guntur I Town', count: 55 },
    { month: '2024-08', station: 'Guntur I Town', count: 62 },
    { month: '2024-09', station: 'Guntur I Town', count: 48 },
    { month: '2024-10', station: 'Guntur I Town', count: 70 },
    { month: '2024-11', station: 'Guntur I Town', count: 65 },
    { month: '2024-12', station: 'Guntur I Town', count: 75 },
    { month: '2025-01', station: 'Guntur I Town', count: 80 },
    { month: '2025-02', station: 'Guntur I Town', count: 72 },
    { month: '2025-03', station: 'Guntur I Town', count: 85 },
    { month: '2025-04', station: 'Guntur I Town', count: 90 },
    { month: '2025-05', station: 'Guntur I Town', count: 88 },
    { month: '2025-06', station: 'Guntur I Town', count: 95 },
]

export const executeQuery = (sql: string): Promise<QueryResult> => {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const lowerSql = sql.toLowerCase();

      if (lowerSql.includes('group by') && lowerSql.includes('guntur')) {
        const columns = ['Crime Type', 'Total FIRs'];
        const rows = MOCK_CRIME_DATA
            .filter(d => d.district === 'Guntur')
            .map(d => [d.crime_type, d.count]);
        resolve({ columns, rows, query: sql });
      } else if (lowerSql.includes('officer_master') && lowerSql.includes('kumar')) {
        const columns = ['Arresting Officer', 'Arrest Date', 'FIR Details'];
        const rows = MOCK_ARREST_DATA
            .filter(d => d.officer_name.includes('Kumar'))
            .map(d => [d.officer_name, d.arrest_date, d.fir_description]);
        resolve({ columns, rows, query: sql });
      } else if (lowerSql.includes('fir') && lowerSql.includes('group by') && lowerSql.includes('month')) {
          const columns = ['Month', 'FIR Count'];
          const rows = MOCK_FIR_TREND.map(d => [d.month, d.count]);
          resolve({columns, rows, query: sql});
      }
      else {
        const columns = ['Crime Type', 'District', 'Total Count'];
        const rows = MOCK_CRIME_DATA.map(d => [d.crime_type, d.district, d.count]);
        resolve({ columns, rows, query: sql });
      }
    }, 1000 + Math.random() * 1000); // Simulate network delay
  });
};
