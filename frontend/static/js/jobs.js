// Path: frontend/static/js/jobs.js

let currentPage = 1;
const limit = 20;

// Load jobs on page load
window.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadJobs();
});

// Load job statistics
async function loadStats() {
    try {
        const response = await fetch('/api/v1/jobs/stats/count');
        const data = await response.json();
        
        document.getElementById('totalJobs').textContent = data.total_jobs || 0;
        document.getElementById('aiScraped').textContent = data.ai_scraped || 0;
        document.getElementById('cdcPosted').textContent = data.cdc_posted || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load jobs list
async function loadJobs() {
    const jobsList = document.getElementById('jobsList');
    jobsList.innerHTML = '<div class="loading">Loading jobs...</div>';
    
    try {
        // Get filter values
        const jobType = document.getElementById('jobTypeFilter').value;
        const source = document.getElementById('sourceFilter').value;
        const location = document.getElementById('locationFilter').value;
        
        // Build query params
        let url = `/api/v1/jobs/list?page=${currentPage}&limit=${limit}`;
        if (jobType) url += `&job_type=${jobType}`;
        if (source) url += `&source=${source}`;
        if (location) url += `&location=${location}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        displayJobs(data.jobs);
        updatePagination(data.pagination);
        
    } catch (error) {
        console.error('Error loading jobs:', error);
        jobsList.innerHTML = '<div class="loading">Error loading jobs. Please try again.</div>';
    }
}

// Display jobs
function displayJobs(jobs) {
    const jobsList = document.getElementById('jobsList');
    
    if (!jobs || jobs.length === 0) {
        jobsList.innerHTML = '<div class="loading">No jobs found.</div>';
        return;
    }
    
    jobsList.innerHTML = jobs.map(job => `
        <div class="job-card">
            <div class="job-title">${job.title}</div>
            <div class="job-company">${job.company}</div>
            <div class="job-details">
                <span class="badge">${job.location}</span>
                <span class="badge">${formatJobType(job.job_type)}</span>
                ${job.source === 'ai_scraped' ? '<span class="badge ai">AI Recommended</span>' : '<span class="badge">CDC Posted</span>'}
            </div>
            <div class="job-details">
                <strong>Salary:</strong> ${job.salary_range || 'Not specified'} |
                <strong>Platform:</strong> ${job.source_platform || 'N/A'} |
                <strong>Views:</strong> ${job.views_count || 0}
            </div>
            <div class="job-description">
                ${truncateText(job.description, 200)}
                ${job.job_url ? `<a href="${job.job_url}" target="_blank">View Full Job</a>` : ''}
            </div>
        </div>
    `).join('');
}

// Update pagination
function updatePagination(pagination) {
    document.getElementById('currentPage').textContent = pagination.page;
    document.getElementById('totalPages').textContent = pagination.total_pages;
    
    document.getElementById('prevBtn').disabled = !pagination.has_prev;
    document.getElementById('nextBtn').disabled = !pagination.has_next;
}

// Pagination functions
function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        loadJobs();
    }
}

function nextPage() {
    currentPage++;
    loadJobs();
}

// Helper functions
function formatJobType(jobType) {
    const types = {
        'full_time': 'Full Time',
        'part_time': 'Part Time',
        'internship': 'Internship',
        'contract': 'Contract',
        'freelance': 'Freelance'
    };
    return types[jobType] || jobType;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}