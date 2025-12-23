/**
 * Analytics Dashboard JavaScript - Fixed Version
 * Handles "table" chart type and canvas reuse issues
 */

const API_BASE = '/api/v1/analytics';
let currentChart = null;
let currentRawData = [];
let currentQueryPipeline = null;

// Get auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('access_token');
}

// API Headers
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`
    };
}

// Initialize dashboard
async function initDashboard() {
    console.log('🚀 Initializing Analytics Dashboard...');
    
    // Check authentication
    if (!getAuthToken()) {
        console.warn('No auth token found, redirecting to login...');
        window.location.href = '/auth/login';
        return;
    }
    
    // Load quick stats (if elements exist)
    const quickStatsElement = document.getElementById('quickStats');
    if (quickStatsElement && document.getElementById('totalStudents')) {
        await loadQuickStats();
        quickStatsElement.classList.remove('hidden');
    }
    
    // Load suggestions
    await loadSuggestions();
    
    // Event listeners
    document.getElementById('submitQueryBtn').addEventListener('click', handleQuerySubmit);
    document.getElementById('queryInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleQuerySubmit();
        }
    });
    
    // Export button
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportToCSV);
    }
    
    // Retry button
    const retryBtn = document.getElementById('retryBtn');
    if (retryBtn) {
        retryBtn.addEventListener('click', handleQuerySubmit);
    }
    
    console.log('✅ Dashboard initialized successfully');
}

// Load quick statistics
async function loadQuickStats() {
    try {
        const response = await fetch(`${API_BASE}/predefined/overview`, {
            headers: getHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            const metrics = data.data.metrics;
            
            document.getElementById('totalStudents').textContent = metrics.total_students.toLocaleString();
            document.getElementById('totalJobs').textContent = metrics.active_jobs.toLocaleString();
            document.getElementById('totalRecs').textContent = metrics.recommendations_generated.toLocaleString();
            
            const appsCount = Math.floor(metrics.recommendations_generated * 0.25);
            document.getElementById('totalApps').textContent = appsCount.toLocaleString();
            
            console.log('✅ Quick stats loaded');
        }
    } catch (error) {
        console.error('❌ Error loading quick stats:', error);
    }
}

// Load query suggestions
async function loadSuggestions() {
    try {
        const response = await fetch(`${API_BASE}/suggestions`, {
            headers: getHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            displaySuggestions(data.suggestions);
            console.log('✅ Suggestions loaded');
        }
    } catch (error) {
        console.error('❌ Error loading suggestions:', error);
    }
}

// Display suggestions
function displaySuggestions(suggestions) {
    const container = document.getElementById('suggestions');
    if (!container) return;
    
    container.innerHTML = '';
    
    const allSuggestions = [
        ...suggestions.student_analytics.slice(0, 3),
        ...suggestions.job_analytics.slice(0, 3),
        ...suggestions.recommendation_analytics.slice(0, 2)
    ];
    
    allSuggestions.forEach(suggestion => {
        const btn = document.createElement('button');
        btn.className = 'suggestion-chip px-4 py-2 text-sm bg-white border-2 border-blue-200 hover:border-blue-400 rounded-full text-blue-700 hover:bg-blue-50 font-medium';
        btn.textContent = suggestion;
        btn.onclick = () => {
            document.getElementById('queryInput').value = suggestion;
            handleQuerySubmit();
        };
        container.appendChild(btn);
    });
}

// Handle query submission
async function handleQuerySubmit() {
    const query = document.getElementById('queryInput').value.trim();
    
    if (!query) {
        alert('Please enter a query');
        return;
    }
    
    console.log('📊 Submitting query:', query);
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ query })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.warn('Unauthorized, redirecting to login...');
                window.location.href = '/auth/login';
                return;
            }
            const errorData = await response.json();
            throw new Error(errorData.detail || `Query failed with status ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ Query response:', data);
        
        currentRawData = data.raw_data || [];
        currentQueryPipeline = data.aggregation_pipeline || null;
        
        displayResults(data);
        
    } catch (error) {
        console.error('❌ Error:', error);
        showError(`Failed to process query: ${error.message}`);
    }
}

// Show loading state
function showLoading() {
    const elements = {
        resultsSection: document.getElementById('resultsSection'),
        llmQuerySection: document.getElementById('llmQuerySection'),
        errorState: document.getElementById('errorState'),
        loadingState: document.getElementById('loadingState'),
        exportBtn: document.getElementById('exportBtn'),
        chartSection: document.getElementById('chartSection')
    };
    
    if (elements.resultsSection) elements.resultsSection.classList.add('hidden');
    if (elements.llmQuerySection) elements.llmQuerySection.classList.add('hidden');
    if (elements.errorState) elements.errorState.classList.add('hidden');
    if (elements.loadingState) elements.loadingState.classList.remove('hidden');
    if (elements.exportBtn) elements.exportBtn.classList.add('hidden');
    if (elements.chartSection) elements.chartSection.classList.add('hidden');
    
    console.log('🔄 Loading state activated');
}

// Show error
function showError(message) {
    const elements = {
        loadingState: document.getElementById('loadingState'),
        resultsSection: document.getElementById('resultsSection'),
        llmQuerySection: document.getElementById('llmQuerySection'),
        errorState: document.getElementById('errorState'),
        errorMessage: document.getElementById('errorMessage')
    };
    
    if (elements.loadingState) elements.loadingState.classList.add('hidden');
    if (elements.resultsSection) elements.resultsSection.classList.add('hidden');
    if (elements.llmQuerySection) elements.llmQuerySection.classList.add('hidden');
    if (elements.errorState) elements.errorState.classList.remove('hidden');
    if (elements.errorMessage) elements.errorMessage.textContent = message;
    
    console.error('❌ Error displayed:', message);
}

// Display results
function displayResults(data) {
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('errorState').classList.add('hidden');
    
    // Display LLM Generated Query
    displayLLMQuery(data);
    
    // Show results section
    document.getElementById('resultsSection').classList.remove('hidden');
    
    // Set query intent
    document.getElementById('queryIntent').textContent = data.query_intent;
    
    // Set insights
    document.getElementById('insights').textContent = data.natural_language_response;
    
    // Handle chart rendering based on type
    const chartSection = document.getElementById('chartSection');
    const chartType = data.chart_type.toLowerCase();
    
    if (chartType === 'table') {
        // Hide chart, only show table
        if (chartSection) chartSection.classList.add('hidden');
        console.log('📋 Table-only view (no chart)');
    } else {
        // Show chart section
        if (chartSection) {
            chartSection.classList.remove('hidden');
            document.getElementById('chartTitle').textContent = data.chart_data.title || 'Analytics Chart';
            renderChart(data.chart_type, data.chart_data);
        }
    }
    
    // Render table
    renderTable(data.raw_data);
    
    // Show export button
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) exportBtn.classList.remove('hidden');
}

// Display LLM Generated MongoDB Query
function displayLLMQuery(data) {
    const llmQuerySection = document.getElementById('llmQuerySection');
    const llmQueryElement = document.getElementById('llmQuery');
    const collectionElement = document.getElementById('queryCollection');
    const chartTypeElement = document.getElementById('chartType');
    
    console.log('=== LLM GENERATED QUERY ===');
    console.log('Collection:', data.collection);
    console.log('Chart Type:', data.chart_type);
    console.log('Aggregation Pipeline:', data.aggregation_pipeline);
    console.log('===========================');
    
    if (!llmQueryElement || !collectionElement || !chartTypeElement) {
        console.warn('⚠️ Some LLM query display elements are missing');
        return;
    }
    
    let queryToDisplay = data.aggregation_pipeline || {
        collection: data.collection,
        chart_type: data.chart_type,
        query_intent: data.query_intent
    };
    
    llmQueryElement.textContent = JSON.stringify(queryToDisplay, null, 2);
    collectionElement.textContent = data.collection || 'Unknown';
    chartTypeElement.textContent = data.chart_type || 'Unknown';
    
    if (llmQuerySection) llmQuerySection.classList.remove('hidden');
    console.log('✅ LLM query displayed');
}

// Copy query to clipboard
function copyQueryToClipboard() {
    const queryText = document.getElementById('llmQuery').textContent;
    
    navigator.clipboard.writeText(queryText).then(() => {
        const btn = event.target;
        const originalText = btn.innerHTML;
        btn.innerHTML = '✅ Copied!';
        setTimeout(() => btn.innerHTML = originalText, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

// Add this to the beginning of your renderChart function to debug:

function renderChart(chartType, chartData) {
    console.log('🎨 Starting chart render...');
    console.log('Chart Type:', chartType);
    console.log('Chart Data:', chartData);
    
    const canvas = document.getElementById('analyticsChart');
    console.log('Canvas element:', canvas);
    
    // Destroy previous chart if exists
    if (currentChart) {
        console.log('🗑️ Destroying previous chart');
        currentChart.destroy();
        currentChart = null;
    }
    
    // Skip if chart type is "table"
    if (chartType.toLowerCase() === 'table') {
        console.log('⏭️ Skipping chart render for table type');
        return;
    }
    
    // Validate chart type
    const validChartTypes = ['bar', 'line', 'pie', 'doughnut', 'radar', 'polarArea'];
    if (!validChartTypes.includes(chartType.toLowerCase())) {
        console.warn(`⚠️ Invalid chart type: ${chartType}, defaulting to bar`);
        chartType = 'bar';
    }
    
    // 🔥 FIX: Handle both data formats
    let labels = [];
    let dataValues = [];
    
    // Check if data is in chartData.labels format
    if (chartData.labels && Array.isArray(chartData.labels)) {
        labels = chartData.labels;
        
        // Get data from datasets or data property
        if (chartData.datasets && chartData.datasets[0]) {
            dataValues = chartData.datasets[0].data;
        } else if (chartData.data) {
            dataValues = chartData.data;
        }
    }
    // Check if data is in datasets format
    else if (chartData.datasets && chartData.datasets[0]) {
        if (chartData.datasets[0].labels) {
            labels = chartData.datasets[0].labels;
        }
        dataValues = chartData.datasets[0].data;
    }
    
    console.log('📊 Processed data:', { labels, dataValues });
    
    // Prepare data
    const data = {
        labels: labels,
        datasets: [{
            label: chartData.title || 'Value',
            data: dataValues,
            backgroundColor: generateColors(labels.length, chartType),
            borderColor: chartType === 'line' ? 'rgba(59, 130, 246, 1)' : undefined,
            borderWidth: chartType === 'line' ? 2 : 1,
            fill: chartType === 'line'
        }]
    };
    
    console.log('📈 Final chart data:', data);
    
    // Chart configuration
    const config = {
        type: chartType,
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: chartType === 'pie' || chartType === 'doughnut',
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: { size: 12 }
                    }
                },
                title: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: { size: 14 },
                    bodyFont: { size: 13 },
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
                            label += typeof value === 'number' ? value.toLocaleString() : value;
                            return label;
                        }
                    }
                }
            },
            scales: chartType !== 'pie' && chartType !== 'doughnut' ? {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        callback: function(value) { return value.toLocaleString(); }
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                },
                x: { grid: { display: false } }
            } : {}
        }
    };
    
    // Create new chart
    try {
        currentChart = new Chart(canvas, config);
        console.log('✅ Chart created successfully!');
    } catch (error) {
        console.error('❌ Chart rendering error:', error);
        console.error('Error details:', error.message);
    }
}

// Generate colors for charts
function generateColors(count, chartType) {
    const baseColors = [
        'rgba(59, 130, 246, 0.8)',    // Blue
        'rgba(16, 185, 129, 0.8)',    // Green
        'rgba(249, 115, 22, 0.8)',    // Orange
        'rgba(139, 92, 246, 0.8)',    // Purple
        'rgba(236, 72, 153, 0.8)',    // Pink
        'rgba(234, 179, 8, 0.8)',     // Yellow
        'rgba(239, 68, 68, 0.8)',     // Red
        'rgba(20, 184, 166, 0.8)',    // Teal
        'rgba(168, 85, 247, 0.8)',    // Violet
        'rgba(34, 197, 94, 0.8)'      // Lime
    ];
    
    if (chartType === 'line') {
        return 'rgba(59, 130, 246, 0.2)';
    }
    
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}
// Render data table
function renderTable(data) {
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
    
    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td class="px-6 py-4 text-center text-gray-500" colspan="100">No data available</td></tr>';
        return;
    }
    
    const columns = Object.keys(data[0]);
    
    // Create table header
    const headerRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.className = 'px-6 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider';
        th.textContent = col.replace(/_/g, ' ');
        headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);
    
    // Create table rows
    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.className = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';
        tr.classList.add('hover:bg-blue-50', 'transition-colors');
        
        columns.forEach(col => {
            const td = document.createElement('td');
            td.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-900';
            
            let value = row[col];
            
            if (value === null || value === undefined) {
                value = '-';
            } else if (typeof value === 'object') {
                value = JSON.stringify(value);
            } else if (typeof value === 'number') {
                value = value.toLocaleString();
            } else if (typeof value === 'boolean') {
                value = value ? '✓' : '✗';
            }
            
            td.textContent = value;
            tr.appendChild(td);
        });
        tableBody.appendChild(tr);
    });
    
    console.log('✅ Table rendered with', data.length, 'rows');
}

// Export to CSV
function exportToCSV() {
    if (!currentRawData || currentRawData.length === 0) {
        alert('No data to export');
        return;
    }
    
    console.log('📥 Exporting', currentRawData.length, 'rows to CSV');
    
    const columns = Object.keys(currentRawData[0]);
    let csv = columns.map(col => `"${col.replace(/"/g, '""')}"`).join(',') + '\n';
    
    currentRawData.forEach(row => {
        const values = columns.map(col => {
            let value = row[col];
            if (value === null || value === undefined) return '';
            value = String(value).replace(/"/g, '""');
            return `"${value}"`;
        });
        csv += values.join(',') + '\n';
    });
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log('✅ CSV exported successfully');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);