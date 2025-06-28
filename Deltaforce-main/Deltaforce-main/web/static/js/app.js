// CCTNS Copilot Engine - Main JavaScript
let currentResults = [];
let currentSQL = '';

async function processTextQuery() {
    const queryText = document.getElementById('queryText').value.trim();
    if (!queryText) {
        alert('Please enter a query');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch('/api/query/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: queryText })
        });
        
        const result = await response.json();
        
        if (result.error) {
            showError(result.error);
        } else {
            displayResults(result);
        }
    } catch (error) {
        showError('Failed to process query: ' + error.message);
    } finally {
        hideLoading();
    }
}

function quickQuery(query) {
    document.getElementById('queryText').value = query;
    processTextQuery();
}

function displayResults(result) {
    currentResults = result.results;
    currentSQL = result.sql;
    
    // Show SQL
    document.getElementById('sqlCode').textContent = result.sql;
    document.getElementById('sqlDisplay').style.display = 'block';
    
    // Show results table
    if (result.results && result.results.length > 0) {
        displayTable(result.results);
        document.getElementById('resultCount').textContent = 
            `Showing ${result.results.length} of ${result.total_rows} records`;
        document.getElementById('resultsTable').style.display = 'block';
        
        // Generate chart if applicable
        if (result.chart_available) {
            generateChart(result.results);
        }
    }
    
    // Show summary
    if (result.summary) {
        document.getElementById('summaryText').textContent = result.summary;
        document.getElementById('summaryContainer').style.display = 'block';
    }
}

function displayTable(data) {
    if (!data || data.length === 0) return;
    
    const container = document.getElementById('tableContainer');
    const headers = Object.keys(data[0]);
    
    let html = '<table class="results-table"><thead><tr>';
    headers.forEach(header => {
        html += `<th>${header}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    data.forEach(row => {
        html += '<tr>';
        headers.forEach(header => {
            html += `<td>${row[header] || ''}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

function generateChart(data) {
    if (!data || data.length === 0) return;
    
    const headers = Object.keys(data[0]);
    if (headers.length < 2) return;
    
    // Simple bar chart
    const labels = data.map(row => row[headers[0]]);
    const values = data.map(row => Number(row[headers[1]]) || 0);
    
    const chartData = [{
        x: labels,
        y: values,
        type: 'bar',
        marker: {
            color: '#1565C0'
        }
    }];
    
    const layout = {
        title: 'CCTNS Query Results',
        xaxis: { title: headers[0] },
        yaxis: { title: headers[1] },
        margin: { t: 50 }
    };
    
    Plotly.newPlot('plotlyChart', chartData, layout);
    document.getElementById('chartContainer').style.display = 'block';
}

function copySql() {
    navigator.clipboard.writeText(currentSQL);
    alert('SQL copied to clipboard!');
}

function exportResults(format) {
    if (!currentResults || currentResults.length === 0) {
        alert('No results to export');
        return;
    }
    
    // Simple CSV export
    if (format === 'csv') {
        const headers = Object.keys(currentResults[0]);
        let csv = headers.join(',') + '\n';
        
        currentResults.forEach(row => {
            const values = headers.map(header => `"${row[header] || ''}"`);
            csv += values.join(',') + '\n';
        });
        
        downloadFile(csv, 'cctns_results.csv', 'text/csv');
    }
}

function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

function speakSummary() {
    const summaryText = document.getElementById('summaryText').textContent;
    if ('speechSynthesis' in window && summaryText) {
        const utterance = new SpeechSynthesisUtterance(summaryText);
        utterance.lang = 'en-IN';
        speechSynthesis.speak(utterance);
    } else {
        alert('Speech synthesis not supported');
    }
}

function showLoading() {
    document.getElementById('loadingSpinner').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingSpinner').style.display = 'none';
}

function showError(message) {
    alert('Error: ' + message);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🛡️ CCTNS Copilot Engine loaded');
});