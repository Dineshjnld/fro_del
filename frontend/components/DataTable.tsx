import React, { useState, useMemo, useRef } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import type { QueryResult } from '../types';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

const downloadCSV = (columns: string[], rows: (string | number)[][]) => {
    const header = columns.join(',');
    const body = rows.map(row => row.join(',')).join('\n');
    const csvContent = `data:text/csv;charset=utf-8,${header}\n${body}`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "cctns_report.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

export const DataTable: React.FC<{ data: QueryResult }> = ({ data }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [isExporting, setIsExporting] = useState(false);
  const rowsPerPage = 10;
  const reportContainerRef = useRef<HTMLDivElement>(null);

  const totalPages = Math.ceil(data.rows.length / rowsPerPage);
  const paginatedRows = data.rows.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleExportPDF = () => {
    const input = reportContainerRef.current;
    if (input) {
      setIsExporting(true);
      setTimeout(() => {
        html2canvas(input, {
          scale: 2,
          useCORS: true,
          backgroundColor: '#ffffff'
        }).then(canvas => {
          const imgData = canvas.toDataURL('image/png');
          const pdf = new jsPDF('p', 'mm', 'a4');
          const pdfWidth = pdf.internal.pageSize.getWidth();
          const pdfHeight = pdf.internal.pageSize.getHeight();
          const canvasWidth = canvas.width;
          const canvasHeight = canvas.height;
          const ratio = canvasWidth / canvasHeight;
          const imgWidthInPdf = pdfWidth;
          const imgHeightInPdf = imgWidthInPdf / ratio;

          let heightLeft = imgHeightInPdf;
          let position = 0;

          pdf.addImage(imgData, 'PNG', 0, position, imgWidthInPdf, imgHeightInPdf);
          heightLeft -= pdfHeight;

          while (heightLeft > 0) {
            position = -heightLeft;
            pdf.addPage();
            pdf.addImage(imgData, 'PNG', 0, position, imgWidthInPdf, imgHeightInPdf);
            heightLeft -= pdfHeight;
          }
          pdf.save('cctns-report.pdf');
        }).finally(() => {
          setIsExporting(false);
        });
      }, 100);
    }
  };

  const chartData = useMemo(() => {
    if (data.rows.length < 1) {
        return [];
    }

    const firstRow = data.rows[0];

    // Strategy 1: Find explicit numeric column for values.
    const numericColumnIndex = firstRow.findIndex(cell => typeof cell === 'number');
    if (numericColumnIndex !== -1) {
        let stringColumnIndex = firstRow.findIndex((cell, index) => typeof cell === 'string' && index !== numericColumnIndex);
        if (stringColumnIndex === -1) { // If no string column, use first non-numeric column as label
             stringColumnIndex = firstRow.findIndex((_, index) => index !== numericColumnIndex);
             if (stringColumnIndex === -1) stringColumnIndex = 0; // Absolute fallback
        }
        
        return data.rows.map(row => ({
            name: String(row[stringColumnIndex]),
            value: Number(row[numericColumnIndex])
        }));
    }

    // Strategy 2: No numeric column, look for a date column to aggregate by month.
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/; // YYYY-MM-DD
    const dateColumnIndex = firstRow.findIndex(cell => typeof cell === 'string' && dateRegex.test(cell));
    
    if (dateColumnIndex !== -1) {
        const aggregation = data.rows.reduce((acc, row) => {
            const dateStr = row[dateColumnIndex] as string;
            const month = dateStr.substring(0, 7); // Group by YYYY-MM
            acc[month] = (acc[month] || 0) + 1;
            return acc;
        }, {} as Record<string, number>);

        return Object.entries(aggregation)
            .map(([month, count]) => ({ name: month, value: count }))
            .sort((a, b) => a.name.localeCompare(b.name));
    }
    
    // Strategy 3: No numeric, no date, aggregate by the first string column if it's categorical.
    const labelColumnIndex = firstRow.findIndex(cell => typeof cell === 'string');
    if (labelColumnIndex !== -1) {
        const aggregation = data.rows.reduce((acc, row) => {
            const label = String(row[labelColumnIndex]);
            acc[label] = (acc[label] || 0) + 1;
            return acc;
        }, {} as Record<string, number>);

        // Only show chart if there's more than one category to compare
        if (Object.keys(aggregation).length > 1) {
             return Object.entries(aggregation)
                .map(([label, count]) => ({ name: label, value: count }));
        }
    }

    // Fallback: Can't generate meaningful chart
    return [];
  }, [data]);

  const ChartComponents = {
    Bar: () => <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" angle={-25} textAnchor="end" height={60} interval={0} /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="value" fill="#3b82f6" /></BarChart>,
    Line: () => <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" angle={-25} textAnchor="end" height={60} interval={0} /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Line type="monotone" dataKey="value" stroke="#16a34a" activeDot={{ r: 8 }} /></LineChart>,
    Pie: () => <PieChart margin={{ top: 5, right: 5, left: 5, bottom: 5 }}><Tooltip /><Legend /><Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={'80%'} fill="#8884d8" labelLine={false} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>{chartData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}</Pie></PieChart>
  };

  return (
    <div className="p-4 flex flex-col h-full bg-gray-50">
      <div className="flex-shrink-0 flex justify-between items-center mb-4 px-4">
        <h2 className="text-xl font-bold text-gray-800">Query Report</h2>
        <div className="space-x-2">
            <button onClick={() => downloadCSV(data.columns, data.rows)} className="px-3 py-1 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50" disabled={isExporting}>Export CSV</button>
            <button onClick={handleExportPDF} className="px-3 py-1 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-50" disabled={isExporting}>
                {isExporting ? 'Exporting...' : 'Export PDF'}
            </button>
        </div>
      </div>
      
      <div ref={reportContainerRef} className="flex-1 overflow-y-auto bg-white rounded-lg shadow p-6">
        <div className="mb-8">
            <h3 className="text-lg font-semibold mb-2 text-gray-700">Data Table</h3>
            <div className="overflow-x-auto border rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-100">
                      <tr>
                      {data.columns.map((col) => (
                          <th key={col} className="px-4 py-3 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">{col}</th>
                      ))}
                      </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                      {paginatedRows.map((row, rowIndex) => (
                      <tr key={rowIndex} className="hover:bg-gray-50">
                          {row.map((cell, cellIndex) => (
                          <td key={cellIndex} className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">{cell}</td>
                          ))}
                      </tr>
                      ))}
                  </tbody>
                </table>
            </div>
            <div className={`flex items-center justify-between pt-3 ${isExporting ? 'hidden' : ''}`}>
                <span className="text-sm text-gray-600">Page {currentPage} of {totalPages}</span>
                <div className="space-x-2">
                  <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1} className="px-3 py-1 border rounded-md text-sm disabled:opacity-50">Previous</button>
                  <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages} className="px-3 py-1 border rounded-md text-sm disabled:opacity-50">Next</button>
                </div>
            </div>
        </div>

        <div>
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Visualizations</h3>
            {chartData.length > 0 ? (
                <div className="space-y-8">
                    <div className="p-4 border rounded-lg shadow-sm">
                        <h4 className="font-semibold text-center mb-2 text-gray-600">Bar Chart</h4>
                        <ResponsiveContainer width="100%" height={350}><ChartComponents.Bar /></ResponsiveContainer>
                    </div>
                    <div className="p-4 border rounded-lg shadow-sm">
                        <h4 className="font-semibold text-center mb-2 text-gray-600">Line Chart</h4>
                        <ResponsiveContainer width="100%" height={350}><ChartComponents.Line /></ResponsiveContainer>
                    </div>
                    <div className="p-4 border rounded-lg shadow-sm">
                        <h4 className="font-semibold text-center mb-2 text-gray-600">Pie Chart</h4>
                        <ResponsiveContainer width="100%" height={350}><ChartComponents.Pie /></ResponsiveContainer>
                    </div>
                </div>
            ) : (
                <div className="text-gray-500 text-center py-8">
                  <p>No meaningful visualizations could be generated for this data.</p>
                  <p className="text-sm mt-1">Charts are created automatically from numeric data or by counting items over time.</p>
                </div>
            )}
        </div>
      </div>
    </div>
  );
};
