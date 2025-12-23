// profile_new.js - Multi-step wizard and resume view
// Place in: frontend/static/js/profile_new.js

let currentStep = 1;
const totalSteps = 5;
let profileData = {};
let isEditMode = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadProfile();
});

// Load profile and determine view
async function loadProfile() {
    try {
        const token = getToken();
        if (!token) {
            window.location.href = '/auth/login';
            return;
        }
        
        const response = await fetch('/api/v1/students/profile', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.profile_data && Object.keys(data.profile_data).length > 0) {
                // Profile exists - show resume view
                profileData = data.profile_data;
                showResumeView();
            } else {
                // No profile - show wizard
                showWizardView();
            }
        } else {
            // Error or no profile - show wizard
            showWizardView();
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        showWizardView();
    }
}

// Show wizard view (first-time setup)
function showWizardView() {
    document.getElementById('wizardView').classList.remove('hidden');
    document.getElementById('resumeView').classList.add('hidden');
    currentStep = 1;
    updateProgress();
}

// Show resume view (profile completed)
function showResumeView() {
    document.getElementById('wizardView').classList.add('hidden');
    document.getElementById('resumeView').classList.remove('hidden');
    populateResumeView();
}

// Enter edit mode (convert resume to wizard)
function enterEditMode() {
    isEditMode = true;
    showWizardView();
    populateWizardForm();
    showNotification('Edit your profile and save changes', 'info');
}

// Populate wizard form with existing data
function populateWizardForm() {
    Object.keys(profileData).forEach(key => {
        const input = document.querySelector(`[name="${key}"]`);
        if (input) {
            input.value = profileData[key] || '';
        }
    });
}

// ========================================
// WIZARD NAVIGATION
// ========================================

function nextStep() {
    if (!validateStep(currentStep)) {
        return;
    }
    
    if (currentStep < totalSteps) {
        currentStep++;
        updateProgress();
        scrollToTop();
    }
}

function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateProgress();
        scrollToTop();
    }
}

function updateProgress() {
    // Update step indicators
    document.querySelectorAll('.step').forEach((step, index) => {
        const stepNum = index + 1;
        if (stepNum < currentStep) {
            step.classList.add('completed');
            step.classList.remove('active');
        } else if (stepNum === currentStep) {
            step.classList.add('active');
            step.classList.remove('completed');
        } else {
            step.classList.remove('active', 'completed');
        }
    });
    
    // Update content visibility
    document.querySelectorAll('.step-content').forEach((content, index) => {
        if (index + 1 === currentStep) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
    
    // Update progress bar fill
    const progress = ((currentStep - 1) / (totalSteps - 1)) * 100;
    document.getElementById('progressFill').style.width = progress + '%';
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========================================
// VALIDATION
// ========================================

function validateStep(step) {
    const stepContent = document.querySelector(`.step-content[data-step="${step}"]`);
    const requiredInputs = stepContent.querySelectorAll('[required]');
    
    for (let input of requiredInputs) {
        if (!input.value.trim()) {
            showNotification(`Please fill in: ${input.previousElementSibling.textContent.replace('*', '').trim()}`, 'warning');
            input.focus();
            return false;
        }
    }
    
    return true;
}

// ========================================
// SAVE PROFILE
// ========================================

async function saveProfile() {
    // Validate final step
    if (!validateStep(currentStep)) {
        return;
    }
    
    // Collect all form data
    const form = document.getElementById('profileForm');
    const formData = new FormData(form);
    const data = {};
    
    formData.forEach((value, key) => {
        data[key] = value;
    });
    
    // Determine if this is create or update
    const user = getUser();
    const isUpdate = isEditMode || (user && user.profile_completed);
    const endpoint = isUpdate ? '/api/v1/students/profile/update' : '/api/v1/students/profile/complete';
    const method = isUpdate ? 'PUT' : 'POST';
    
    try {
        showNotification('Saving your profile...', 'info');
        
        const token = getToken();
        const response = await fetch(endpoint, {
            method: method,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Update user data
            if (user) {
                user.profile_completed = true;
                setUser(user);
            }
            
            profileData = data;
            isEditMode = false;
            
            showNotification('✅ Profile saved successfully!', 'success');
            
            // Show resume view
            setTimeout(() => {
                showResumeView();
            }, 1000);
        } else {
            showNotification('❌ ' + (result.detail || 'Failed to save profile'), 'error');
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        showNotification('❌ Error saving profile. Please try again.', 'error');
    }
}

// ========================================
// RESUME VIEW POPULATION
// ========================================

function populateResumeView() {
    const user = getUser();
    
    // Header
    document.getElementById('profileName').textContent = profileData.full_name || 'N/A';
    document.getElementById('profileTitle').textContent = `${profileData.degree || 'Student'} - ${profileData.branch || ''}`;
    document.getElementById('profileEmail').textContent = user?.email || '-';
    document.getElementById('profilePhone').textContent = profileData.phone || '-';
    document.getElementById('profileLocation').textContent = profileData.location || '-';
    
    // Summary
    const summary = profileData.summary || 'No summary provided';
    document.getElementById('profileSummary').textContent = summary;
    toggleSection('summarySection', summary !== 'No summary provided');
    
    // Education
    document.getElementById('profileCollege').textContent = profileData.college_name || '-';
    document.getElementById('profileDegree').textContent = `${profileData.degree || '-'} in ${profileData.branch || '-'}`;
    document.getElementById('profileYear').textContent = getYearText(profileData.year_of_study);
    document.getElementById('profileCGPA').textContent = profileData.cgpa || '-';
    
    // Technical Skills
    populateSkills('technicalSkillsContainer', profileData.technical_skills);
    
    // Soft Skills
    const hasSoftSkills = profileData.soft_skills && profileData.soft_skills.trim();
    populateSkills('softSkillsContainer', profileData.soft_skills);
    toggleSection('softSkillsSection', hasSoftSkills);
    
    // Experience
    const experience = profileData.experience || '';
    document.getElementById('profileExperience').textContent = experience || 'No experience added yet';
    toggleSection('experienceSection', experience);
    
    // Projects
    const projects = profileData.projects || '';
    document.getElementById('profileProjects').textContent = projects || 'No projects added yet';
    toggleSection('projectsSection', projects);
    
    // Certifications
    const certifications = profileData.certifications || '';
    document.getElementById('profileCertifications').textContent = certifications || 'No certifications added yet';
    toggleSection('certificationsSection', certifications);
    
    // Links
    populateLinks();
    
    // Career Preferences
    document.getElementById('profileRoles').textContent = profileData.preferred_roles || '-';
    document.getElementById('profileIndustries').textContent = profileData.preferred_industries || '-';
    document.getElementById('profileSalary').textContent = profileData.expected_salary || '-';
    document.getElementById('profileRelocate').textContent = getRelocateText(profileData.willing_to_relocate);
}

function populateSkills(containerId, skillsString) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (!skillsString || !skillsString.trim()) {
        container.innerHTML = '<p class="text-slate-500 italic">No skills added</p>';
        return;
    }
    
    const skills = skillsString.split(',').map(s => s.trim()).filter(s => s);
    
    skills.forEach(skill => {
        const tag = document.createElement('span');
        tag.className = 'skill-tag';
        tag.textContent = skill;
        container.appendChild(tag);
    });
}

function populateLinks() {
    const container = document.getElementById('profileLinks');
    container.innerHTML = '';
    
    const links = [
        { url: profileData.linkedin, icon: 'linkedin', label: 'LinkedIn', color: 'bg-blue-50 text-blue-600' },
        { url: profileData.github, icon: 'github', label: 'GitHub', color: 'bg-slate-50 text-slate-700' },
        { url: profileData.portfolio, icon: 'globe', label: 'Portfolio', color: 'bg-purple-50 text-purple-600' },
        { url: profileData.resume_link, icon: 'file-pdf', label: 'Resume', color: 'bg-red-50 text-red-600' }
    ];
    
    let hasLinks = false;
    
    links.forEach(link => {
        if (link.url && link.url.trim()) {
            hasLinks = true;
            const a = document.createElement('a');
            a.href = link.url;
            a.target = '_blank';
            a.className = `link-button ${link.color}`;
            a.innerHTML = `<i class="fab fa-${link.icon}"></i> ${link.label}`;
            container.appendChild(a);
        }
    });
    
    if (!hasLinks) {
        container.innerHTML = '<p class="text-slate-500 italic">No links added</p>';
    }
    
    toggleSection('linksSection', hasLinks);
}

function toggleSection(sectionId, show) {
    const section = document.getElementById(sectionId);
    if (section) {
        if (show) {
            section.classList.remove('hidden');
        } else {
            section.classList.add('hidden');
        }
    }
}

function getYearText(year) {
    const yearMap = {
        '1': '1st Year',
        '2': '2nd Year',
        '3': '3rd Year',
        '4': '4th Year',
        'graduated': 'Graduated'
    };
    return yearMap[year] || '-';
}

function getRelocateText(value) {
    const map = {
        'yes': 'Yes',
        'no': 'No',
        'maybe': 'Maybe'
    };
    return map[value] || '-';
}