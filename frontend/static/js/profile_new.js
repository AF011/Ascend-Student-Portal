// profile_new.js - Multi-step wizard with array management
// Enhanced to match new backend schema with nested objects
// FULLY FIXED VERSION

let currentStep = 1;
const totalSteps = 5;
let profileData = {
    // Personal
    full_name: '',
    phone: '',
    location: '',
    gender: '',
    date_of_birth: null,
    
    // Arrays
    education: [],
    skills: [],
    experience: [],
    projects: [],
    certifications: [],
    
    // Nested objects
    preferences: {},
    links: {},
    
    // Additional
    summary: '',
    domain_expertise: '',
    languages: '',
    achievements: '',
    total_experience_years: 0,
    current_role: 'Student',
    current_company: ''
};

let isEditMode = false;

// Temporary edit indices for array items
let editingEducation = -1;
let editingSkill = -1;
let editingExperience = -1;
let editingProject = -1;
let editingCertification = -1;

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    loadProfile();
    setupEventListeners();
});

function setupEventListeners() {
    // Array form submissions
    const educationForm = document.getElementById('educationForm');
    if (educationForm) {
        educationForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveEducationEntry();
        });
    }
    
    const skillForm = document.getElementById('skillForm');
    if (skillForm) {
        skillForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveSkillEntry();
        });
    }
    
    const experienceForm = document.getElementById('experienceForm');
    if (experienceForm) {
        experienceForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveExperienceEntry();
        });
    }
    
    const projectForm = document.getElementById('projectForm');
    if (projectForm) {
        projectForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveProjectEntry();
        });
    }
    
    const certificationForm = document.getElementById('certificationForm');
    if (certificationForm) {
        certificationForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveCertificationEntry();
        });
    }
}

// ========================================
// LOAD PROFILE
// ========================================

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
                // Profile exists - assign and sanitize data
                profileData = data.profile_data;
                
                // **CRITICAL FIX: Sanitize data before using**
                sanitizeProfileData();
                
                console.log('Profile loaded:', profileData);
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

// ========================================
// DATA SANITIZATION
// ========================================

function sanitizeProfileData() {
    console.log('Sanitizing profile data...');
    
    // Ensure all arrays are actually arrays
    if (!Array.isArray(profileData.education)) {
        profileData.education = [];
    }
    if (!Array.isArray(profileData.skills)) {
        profileData.skills = [];
    }
    if (!Array.isArray(profileData.experience)) {
        profileData.experience = [];
    }
    if (!Array.isArray(profileData.projects)) {
        profileData.projects = [];
    }
    if (!Array.isArray(profileData.certifications)) {
        profileData.certifications = [];
    }
    
    // Ensure preferences is an object
    if (!profileData.preferences || typeof profileData.preferences !== 'object') {
        profileData.preferences = {
            employment_type: [],
            work_mode: [],
            preferred_roles: null,
            preferred_industries: null,
            expected_salary: null,
            willing_to_relocate: null,
            notice_period: null,
            availability_date: null,
            preferred_locations: null
        };
    } else {
        // Ensure arrays within preferences
        if (!Array.isArray(profileData.preferences.employment_type)) {
            profileData.preferences.employment_type = [];
        }
        if (!Array.isArray(profileData.preferences.work_mode)) {
            profileData.preferences.work_mode = [];
        }
    }
    
    // Ensure links is an object
    if (!profileData.links || typeof profileData.links !== 'object') {
        profileData.links = {
            linkedin: null,
            github: null,
            portfolio: null,
            resume_link: null,
            twitter: null,
            leetcode: null
        };
    }
    
    // Fix tech_stack in projects if it's a string
    if (Array.isArray(profileData.projects)) {
        profileData.projects = profileData.projects.map(proj => {
            if (typeof proj.tech_stack === 'string') {
                proj.tech_stack = proj.tech_stack.split(',').map(s => s.trim()).filter(s => s);
            } else if (!Array.isArray(proj.tech_stack)) {
                proj.tech_stack = [];
            }
            return proj;
        });
    }
    
    console.log('Profile data sanitized successfully');
}

// ========================================
// VIEW MANAGEMENT
// ========================================

function showWizardView() {
    document.getElementById('wizardView').classList.remove('hidden');
    document.getElementById('resumeView').classList.add('hidden');
    currentStep = 1;
    updateProgress();
}

function showResumeView() {
    document.getElementById('wizardView').classList.add('hidden');
    document.getElementById('resumeView').classList.remove('hidden');
    populateResumeView();
}

function enterEditMode() {
    isEditMode = true;
    showWizardView();
    populateWizardForm();
    showNotification('Edit your profile and save changes', 'info');
}

function populateWizardForm() {
    console.log('Populating wizard form with data:', profileData);
    
    // Sanitize data first
    sanitizeProfileData();
    
    // Personal info - with null safety
    setInputValue('full_name', profileData.full_name || '');
    setInputValue('phone', profileData.phone || '');
    setInputValue('location', profileData.location || '');
    setInputValue('gender', profileData.gender || '');
    setInputValue('date_of_birth', profileData.date_of_birth || '');
    
    // Additional fields - with null safety
    setInputValue('domain_expertise', profileData.domain_expertise || '');
    setInputValue('languages', profileData.languages || '');
    setInputValue('summary', profileData.summary || '');
    setInputValue('achievements', profileData.achievements || '');
    setInputValue('total_experience_years', profileData.total_experience_years || 0);
    setInputValue('current_role', profileData.current_role || 'Student');
    setInputValue('current_company', profileData.current_company || '');
    
    // Populate arrays (already sanitized)
    renderEducationList();
    renderSkillsList();
    renderExperienceList();
    renderProjectsList();
    renderCertificationsList();
    
    // Populate preferences (already sanitized)
    // First, clear all existing checkboxes
    document.querySelectorAll('input[name="employment_type"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('input[name="work_mode"]').forEach(cb => cb.checked = false);
    
    const pref = profileData.preferences;
    
    // Employment type checkboxes
    if (pref.employment_type && Array.isArray(pref.employment_type)) {
        pref.employment_type.forEach(type => {
            const checkbox = document.querySelector(`input[name="employment_type"][value="${type}"]`);
            if (checkbox) checkbox.checked = true;
        });
    }
    
    // Work mode checkboxes
    if (pref.work_mode && Array.isArray(pref.work_mode)) {
        pref.work_mode.forEach(mode => {
            const checkbox = document.querySelector(`input[name="work_mode"][value="${mode}"]`);
            if (checkbox) checkbox.checked = true;
        });
    }
    
    // Other preference fields
    setInputValue('preferred_roles', pref.preferred_roles || '');
    setInputValue('preferred_industries', pref.preferred_industries || '');
    setInputValue('expected_salary', pref.expected_salary || '');
    setInputValue('willing_to_relocate', pref.willing_to_relocate || '');
    setInputValue('notice_period', pref.notice_period || '');
    setInputValue('availability_date', pref.availability_date || '');
    setInputValue('preferred_locations', pref.preferred_locations || '');
    
    // Populate links (already sanitized)
    setInputValue('linkedin', profileData.links.linkedin || '');
    setInputValue('github', profileData.links.github || '');
    setInputValue('portfolio', profileData.links.portfolio || '');
    setInputValue('resume_link', profileData.links.resume_link || '');
    setInputValue('twitter', profileData.links.twitter || '');
    setInputValue('leetcode', profileData.links.leetcode || '');
    
    console.log('Form populated successfully');
}

function setInputValue(name, value) {
    const input = document.querySelector(`[name="${name}"]`);
    if (input) {
        // Handle null, undefined, or empty values
        if (value === null || value === undefined) {
            input.value = '';
        } else {
            input.value = value;
        }
    }
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
            const label = input.previousElementSibling?.textContent?.replace('*', '').trim() || 'This field';
            showNotification(`Please fill in: ${label}`, 'warning');
            input.focus();
            return false;
        }
    }
    
    // Additional validation for specific steps
    if (step === 2 && profileData.education.length === 0) {
        showNotification('Please add at least one education entry', 'warning');
        return false;
    }
    
    if (step === 3 && profileData.skills.length === 0) {
        showNotification('Please add at least one skill', 'warning');
        return false;
    }
    
    return true;
}

// ========================================
// EDUCATION MANAGEMENT
// ========================================

function openEducationForm() {
    editingEducation = -1;
    document.getElementById('educationForm').reset();
    document.getElementById('educationModal').classList.remove('hidden');
    document.getElementById('educationModalTitle').textContent = 'Add Education';
    document.getElementById('saveEducationBtn').textContent = 'Add Education';
}

function closeEducationModal() {
    document.getElementById('educationModal').classList.add('hidden');
    editingEducation = -1;
}

function editEducation(index) {
    editingEducation = index;
    const edu = profileData.education[index];
    
    setInputValue('edu_level', edu.level);
    setInputValue('edu_board_university', edu.board_university);
    setInputValue('edu_school_college', edu.school_college);
    setInputValue('edu_year', edu.year);
    setInputValue('edu_percentage_cgpa', edu.percentage_cgpa);
    setInputValue('edu_degree', edu.degree);
    setInputValue('edu_branch', edu.branch);
    
    document.getElementById('educationModal').classList.remove('hidden');
    document.getElementById('educationModalTitle').textContent = 'Edit Education';
    document.getElementById('saveEducationBtn').textContent = 'Update Education';
}

function saveEducationEntry() {
    const degreeValue = document.querySelector('[name="edu_degree"]')?.value;
    const branchValue = document.querySelector('[name="edu_branch"]')?.value;
    
    const education = {
        level: document.querySelector('[name="edu_level"]').value,
        board_university: document.querySelector('[name="edu_board_university"]').value,
        school_college: document.querySelector('[name="edu_school_college"]').value,
        year: parseInt(document.querySelector('[name="edu_year"]').value),
        percentage_cgpa: parseFloat(document.querySelector('[name="edu_percentage_cgpa"]').value),
        degree: (degreeValue && degreeValue.trim()) ? degreeValue.trim() : null,
        branch: (branchValue && branchValue.trim()) ? branchValue.trim() : null
    };
    
    if (editingEducation >= 0) {
        profileData.education[editingEducation] = education;
    } else {
        profileData.education.push(education);
    }
    
    renderEducationList();
    closeEducationModal();
    showNotification('Education entry saved', 'success');
}

function deleteEducation(index) {
    if (confirm('Are you sure you want to delete this education entry?')) {
        profileData.education.splice(index, 1);
        renderEducationList();
        showNotification('Education entry deleted', 'success');
    }
}

function renderEducationList() {
    const container = document.getElementById('educationList');
    
    if (profileData.education.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic text-center py-4">No education entries added yet. Click "Add Education" to get started.</p>';
        return;
    }
    
    container.innerHTML = profileData.education.map((edu, index) => `
        <div class="array-item">
            <div class="flex-1">
                <div class="font-semibold text-slate-800">${edu.school_college}</div>
                <div class="text-sm text-slate-600">
                    ${edu.degree ? `${edu.degree} in ${edu.branch || 'N/A'}` : edu.level} - ${edu.board_university}
                </div>
                <div class="text-sm text-slate-500">
                    Year: ${edu.year} | Score: ${edu.percentage_cgpa}
                </div>
            </div>
            <div class="flex gap-2">
                <button type="button" onclick="editEducation(${index})" class="btn-icon-edit" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button type="button" onclick="deleteEducation(${index})" class="btn-icon-delete" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// ========================================
// SKILLS MANAGEMENT
// ========================================

function openSkillForm() {
    editingSkill = -1;
    document.getElementById('skillForm').reset();
    document.getElementById('skillModal').classList.remove('hidden');
    document.getElementById('skillModalTitle').textContent = 'Add Skill';
    document.getElementById('saveSkillBtn').textContent = 'Add Skill';
}

function closeSkillModal() {
    document.getElementById('skillModal').classList.add('hidden');
    editingSkill = -1;
}

function editSkill(index) {
    editingSkill = index;
    const skill = profileData.skills[index];
    
    setInputValue('skill_name', skill.name);
    setInputValue('skill_proficiency', skill.proficiency);
    setInputValue('skill_category', skill.category);
    
    document.getElementById('skillModal').classList.remove('hidden');
    document.getElementById('skillModalTitle').textContent = 'Edit Skill';
    document.getElementById('saveSkillBtn').textContent = 'Update Skill';
}

function saveSkillEntry() {
    const categoryValue = document.querySelector('[name="skill_category"]')?.value;
    
    const skill = {
        name: document.querySelector('[name="skill_name"]').value.trim(),
        proficiency: document.querySelector('[name="skill_proficiency"]').value,
        category: (categoryValue && categoryValue.trim()) ? categoryValue.trim() : null
    };
    
    if (editingSkill >= 0) {
        profileData.skills[editingSkill] = skill;
    } else {
        profileData.skills.push(skill);
    }
    
    renderSkillsList();
    closeSkillModal();
    showNotification('Skill saved', 'success');
}

function deleteSkill(index) {
    if (confirm('Are you sure you want to delete this skill?')) {
        profileData.skills.splice(index, 1);
        renderSkillsList();
        showNotification('Skill deleted', 'success');
    }
}

function renderSkillsList() {
    const container = document.getElementById('skillsList');
    
    if (profileData.skills.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic text-center py-4">No skills added yet. Click "Add Skill" to get started.</p>';
        return;
    }
    
    container.innerHTML = profileData.skills.map((skill, index) => `
        <div class="array-item">
            <div class="flex-1">
                <div class="font-semibold text-slate-800">${skill.name}</div>
                <div class="text-sm text-slate-600">
                    ${skill.proficiency}${skill.category ? ` • ${skill.category}` : ''}
                </div>
            </div>
            <div class="flex gap-2">
                <button type="button" onclick="editSkill(${index})" class="btn-icon-edit" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button type="button" onclick="deleteSkill(${index})" class="btn-icon-delete" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// ========================================
// EXPERIENCE MANAGEMENT
// ========================================

function openExperienceForm() {
    editingExperience = -1;
    document.getElementById('experienceForm').reset();
    document.getElementById('experienceModal').classList.remove('hidden');
    document.getElementById('experienceModalTitle').textContent = 'Add Experience';
    document.getElementById('saveExperienceBtn').textContent = 'Add Experience';
}

function closeExperienceModal() {
    document.getElementById('experienceModal').classList.add('hidden');
    editingExperience = -1;
}

function editExperience(index) {
    editingExperience = index;
    const exp = profileData.experience[index];
    
    setInputValue('exp_company', exp.company);
    setInputValue('exp_role', exp.role);
    setInputValue('exp_start_date', exp.start_date);
    setInputValue('exp_end_date', exp.end_date);
    document.querySelector('[name="exp_is_current"]').checked = exp.is_current || false;
    setInputValue('exp_description', exp.description);
    setInputValue('exp_location', exp.location);
    
    document.getElementById('experienceModal').classList.remove('hidden');
    document.getElementById('experienceModalTitle').textContent = 'Edit Experience';
    document.getElementById('saveExperienceBtn').textContent = 'Update Experience';
}

function saveExperienceEntry() {
    const endDateValue = document.querySelector('[name="exp_end_date"]')?.value;
    const locationValue = document.querySelector('[name="exp_location"]')?.value;
    
    const experience = {
        company: document.querySelector('[name="exp_company"]').value.trim(),
        role: document.querySelector('[name="exp_role"]').value.trim(),
        start_date: document.querySelector('[name="exp_start_date"]').value.trim(),
        end_date: (endDateValue && endDateValue.trim()) ? endDateValue.trim() : null,
        is_current: document.querySelector('[name="exp_is_current"]').checked,
        description: document.querySelector('[name="exp_description"]').value.trim(),
        location: (locationValue && locationValue.trim()) ? locationValue.trim() : null
    };
    
    if (editingExperience >= 0) {
        profileData.experience[editingExperience] = experience;
    } else {
        profileData.experience.push(experience);
    }
    
    renderExperienceList();
    closeExperienceModal();
    showNotification('Experience saved', 'success');
}

function deleteExperience(index) {
    if (confirm('Are you sure you want to delete this experience?')) {
        profileData.experience.splice(index, 1);
        renderExperienceList();
        showNotification('Experience deleted', 'success');
    }
}

function renderExperienceList() {
    const container = document.getElementById('experienceList');
    
    if (profileData.experience.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic text-center py-4">No experience entries added yet. Click "Add Experience" to get started.</p>';
        return;
    }
    
    container.innerHTML = profileData.experience.map((exp, index) => `
        <div class="array-item">
            <div class="flex-1">
                <div class="font-semibold text-slate-800">${exp.role} at ${exp.company}</div>
                <div class="text-sm text-slate-600">
                    ${exp.start_date} - ${exp.is_current ? 'Present' : exp.end_date || 'N/A'}
                    ${exp.location ? ` • ${exp.location}` : ''}
                </div>
                <div class="text-sm text-slate-500 mt-1">${exp.description.substring(0, 100)}${exp.description.length > 100 ? '...' : ''}</div>
            </div>
            <div class="flex gap-2">
                <button type="button" onclick="editExperience(${index})" class="btn-icon-edit" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button type="button" onclick="deleteExperience(${index})" class="btn-icon-delete" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// ========================================
// PROJECTS MANAGEMENT
// ========================================

function openProjectForm() {
    editingProject = -1;
    document.getElementById('projectForm').reset();
    document.getElementById('projectModal').classList.remove('hidden');
    document.getElementById('projectModalTitle').textContent = 'Add Project';
    document.getElementById('saveProjectBtn').textContent = 'Add Project';
}

function closeProjectModal() {
    document.getElementById('projectModal').classList.add('hidden');
    editingProject = -1;
}

function editProject(index) {
    editingProject = index;
    const proj = profileData.projects[index];
    
    setInputValue('proj_title', proj.title);
    setInputValue('proj_description', proj.description);
    
    // Handle tech_stack - it's always an array after sanitization
    if (Array.isArray(proj.tech_stack)) {
        setInputValue('proj_tech_stack', proj.tech_stack.join(', '));
    } else {
        setInputValue('proj_tech_stack', '');
    }
    
    setInputValue('proj_link', proj.link);
    setInputValue('proj_github_link', proj.github_link);
    setInputValue('proj_start_date', proj.start_date);
    setInputValue('proj_end_date', proj.end_date);
    
    document.getElementById('projectModal').classList.remove('hidden');
    document.getElementById('projectModalTitle').textContent = 'Edit Project';
    document.getElementById('saveProjectBtn').textContent = 'Update Project';
}

function saveProjectEntry() {
    const techStackInput = document.querySelector('[name="proj_tech_stack"]').value;
    const tech_stack = techStackInput.split(',').map(s => s.trim()).filter(s => s);
    
    // Validate tech_stack has at least one item
    if (tech_stack.length === 0) {
        showNotification('Please add at least one technology in Tech Stack', 'warning');
        return;
    }
    
    const linkValue = document.querySelector('[name="proj_link"]')?.value;
    const githubValue = document.querySelector('[name="proj_github_link"]')?.value;
    const startDateValue = document.querySelector('[name="proj_start_date"]')?.value;
    const endDateValue = document.querySelector('[name="proj_end_date"]')?.value;
    
    const project = {
        title: document.querySelector('[name="proj_title"]').value.trim(),
        description: document.querySelector('[name="proj_description"]').value.trim(),
        tech_stack: tech_stack,
        link: (linkValue && linkValue.trim()) ? linkValue.trim() : null,
        github_link: (githubValue && githubValue.trim()) ? githubValue.trim() : null,
        start_date: (startDateValue && startDateValue.trim()) ? startDateValue.trim() : null,
        end_date: (endDateValue && endDateValue.trim()) ? endDateValue.trim() : null
    };
    
    if (editingProject >= 0) {
        profileData.projects[editingProject] = project;
    } else {
        profileData.projects.push(project);
    }
    
    renderProjectsList();
    closeProjectModal();
    showNotification('Project saved', 'success');
}

function deleteProject(index) {
    if (confirm('Are you sure you want to delete this project?')) {
        profileData.projects.splice(index, 1);
        renderProjectsList();
        showNotification('Project deleted', 'success');
    }
}

function renderProjectsList() {
    const container = document.getElementById('projectsList');
    
    if (profileData.projects.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic text-center py-4">No projects added yet. Click "Add Project" to get started.</p>';
        return;
    }
    
    container.innerHTML = profileData.projects.map((proj, index) => {
        // Handle tech_stack display
        let techStackDisplay = '';
        if (Array.isArray(proj.tech_stack)) {
            techStackDisplay = proj.tech_stack.join(', ');
        } else {
            techStackDisplay = 'N/A';
        }
        
        return `
            <div class="array-item">
                <div class="flex-1">
                    <div class="font-semibold text-slate-800">${proj.title}</div>
                    <div class="text-sm text-slate-600">${techStackDisplay}</div>
                    <div class="text-sm text-slate-500 mt-1">${proj.description.substring(0, 100)}${proj.description.length > 100 ? '...' : ''}</div>
                </div>
                <div class="flex gap-2">
                    <button type="button" onclick="editProject(${index})" class="btn-icon-edit" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" onclick="deleteProject(${index})" class="btn-icon-delete" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// ========================================
// CERTIFICATIONS MANAGEMENT
// ========================================

function openCertificationForm() {
    editingCertification = -1;
    document.getElementById('certificationForm').reset();
    document.getElementById('certificationModal').classList.remove('hidden');
    document.getElementById('certificationModalTitle').textContent = 'Add Certification';
    document.getElementById('saveCertificationBtn').textContent = 'Add Certification';
}

function closeCertificationModal() {
    document.getElementById('certificationModal').classList.add('hidden');
    editingCertification = -1;
}

function editCertification(index) {
    editingCertification = index;
    const cert = profileData.certifications[index];
    
    setInputValue('cert_name', cert.name);
    setInputValue('cert_issuer', cert.issuer);
    setInputValue('cert_issue_date', cert.issue_date);
    setInputValue('cert_expiry_date', cert.expiry_date);
    setInputValue('cert_credential_id', cert.credential_id);
    setInputValue('cert_credential_url', cert.credential_url);
    
    document.getElementById('certificationModal').classList.remove('hidden');
    document.getElementById('certificationModalTitle').textContent = 'Edit Certification';
    document.getElementById('saveCertificationBtn').textContent = 'Update Certification';
}

function saveCertificationEntry() {
    const expiryDateValue = document.querySelector('[name="cert_expiry_date"]')?.value;
    const credentialIdValue = document.querySelector('[name="cert_credential_id"]')?.value;
    const credentialUrlValue = document.querySelector('[name="cert_credential_url"]')?.value;
    
    const certification = {
        name: document.querySelector('[name="cert_name"]').value.trim(),
        issuer: document.querySelector('[name="cert_issuer"]').value.trim(),
        issue_date: document.querySelector('[name="cert_issue_date"]').value.trim(),
        expiry_date: (expiryDateValue && expiryDateValue.trim()) ? expiryDateValue.trim() : null,
        credential_id: (credentialIdValue && credentialIdValue.trim()) ? credentialIdValue.trim() : null,
        credential_url: (credentialUrlValue && credentialUrlValue.trim()) ? credentialUrlValue.trim() : null
    };
    
    if (editingCertification >= 0) {
        profileData.certifications[editingCertification] = certification;
    } else {
        profileData.certifications.push(certification);
    }
    
    renderCertificationsList();
    closeCertificationModal();
    showNotification('Certification saved', 'success');
}

function deleteCertification(index) {
    if (confirm('Are you sure you want to delete this certification?')) {
        profileData.certifications.splice(index, 1);
        renderCertificationsList();
        showNotification('Certification deleted', 'success');
    }
}

function renderCertificationsList() {
    const container = document.getElementById('certificationsList');
    
    if (profileData.certifications.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic text-center py-4">No certifications added yet. Click "Add Certification" to get started.</p>';
        return;
    }
    
    container.innerHTML = profileData.certifications.map((cert, index) => `
        <div class="array-item">
            <div class="flex-1">
                <div class="font-semibold text-slate-800">${cert.name}</div>
                <div class="text-sm text-slate-600">${cert.issuer} • ${cert.issue_date}</div>
                ${cert.credential_id ? `<div class="text-sm text-slate-500">ID: ${cert.credential_id}</div>` : ''}
            </div>
            <div class="flex gap-2">
                <button type="button" onclick="editCertification(${index})" class="btn-icon-edit" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button type="button" onclick="deleteCertification(${index})" class="btn-icon-delete" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// ========================================
// SAVE PROFILE
// ========================================

async function saveProfile() {
    // Helper function to get value or null
    const getValueOrNull = (selector) => {
        const element = document.querySelector(selector);
        if (!element) return null;
        const value = element.value;
        return (value && value.trim()) ? value.trim() : null;
    };
    
    // Collect personal data
    profileData.full_name = document.querySelector('[name="full_name"]').value.trim();
    profileData.phone = document.querySelector('[name="phone"]').value.trim();
    profileData.location = document.querySelector('[name="location"]').value.trim();
    profileData.gender = getValueOrNull('[name="gender"]');
    profileData.date_of_birth = getValueOrNull('[name="date_of_birth"]');
    
    // Additional fields
    profileData.domain_expertise = getValueOrNull('[name="domain_expertise"]');
    profileData.languages = getValueOrNull('[name="languages"]');
    profileData.summary = getValueOrNull('[name="summary"]');
    profileData.achievements = getValueOrNull('[name="achievements"]');
    
    const expYears = document.querySelector('[name="total_experience_years"]')?.value;
    profileData.total_experience_years = expYears ? parseInt(expYears) : 0;
    
    profileData.current_role = getValueOrNull('[name="current_role"]') || 'Student';
    profileData.current_company = getValueOrNull('[name="current_company"]');
    
    // Career Preferences
    const employment_type = Array.from(document.querySelectorAll('[name="employment_type"]:checked')).map(el => el.value);
    const work_mode = Array.from(document.querySelectorAll('[name="work_mode"]:checked')).map(el => el.value);
    
    profileData.preferences = {
        employment_type: employment_type,
        work_mode: work_mode,
        preferred_roles: getValueOrNull('[name="preferred_roles"]'),
        preferred_industries: getValueOrNull('[name="preferred_industries"]'),
        expected_salary: getValueOrNull('[name="expected_salary"]'),
        willing_to_relocate: getValueOrNull('[name="willing_to_relocate"]'),
        notice_period: getValueOrNull('[name="notice_period"]'),
        availability_date: getValueOrNull('[name="availability_date"]'),
        preferred_locations: getValueOrNull('[name="preferred_locations"]')
    };
    
    // Links
    profileData.links = {
        linkedin: getValueOrNull('[name="linkedin"]'),
        github: getValueOrNull('[name="github"]'),
        portfolio: getValueOrNull('[name="portfolio"]'),
        resume_link: getValueOrNull('[name="resume_link"]'),
        twitter: getValueOrNull('[name="twitter"]'),
        leetcode: getValueOrNull('[name="leetcode"]')
    };
    
    // Determine if this is create or update
    const user = getUser();
    const isUpdate = isEditMode || (user && user.profile_completed);
    const endpoint = isUpdate ? '/api/v1/students/profile/update' : '/api/v1/students/profile/complete';
    const method = isUpdate ? 'PUT' : 'POST';
    
    try {
        showNotification('Saving your profile...', 'info');
        
        // Debug: Log the payload
        console.log('Sending profile data:', JSON.stringify(profileData, null, 2));
        
        const token = getToken();
        const response = await fetch(endpoint, {
            method: method,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ profile_data: profileData })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Update user data
            if (user) {
                user.profile_completed = true;
                setUser(user);
            }
            
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
    
    // Sanitize data before populating
    sanitizeProfileData();
    
    // Header
    document.getElementById('profileName').textContent = profileData.full_name || 'N/A';
    document.getElementById('profileTitle').textContent = `${profileData.current_role || 'Student'}${profileData.current_company ? ` at ${profileData.current_company}` : ''}`;
    document.getElementById('profileEmail').textContent = user?.email || '-';
    document.getElementById('profilePhone').textContent = profileData.phone || '-';
    document.getElementById('profileLocation').textContent = profileData.location || '-';
    
    // Summary
    const summary = profileData.summary || 'No summary provided';
    document.getElementById('profileSummary').textContent = summary;
    toggleSection('summarySection', summary !== 'No summary provided');
    
    // Populate sections
    populateEducationResume();
    populateSkillsResume();
    populateExperienceResume();
    populateProjectsResume();
    populateCertificationsResume();
    populateLinks();
    populatePreferencesResume();
}

function populateEducationResume() {
    const container = document.getElementById('educationResumeContainer');
    
    if (!container) return;
    
    if (!Array.isArray(profileData.education) || profileData.education.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic">No education information added</p>';
        return;
    }
    
    container.innerHTML = profileData.education.map(edu => `
        <div class="resume-item mb-4">
            <div class="font-semibold text-slate-800">${edu.school_college || 'N/A'}</div>
            <div class="text-slate-600">
                ${edu.degree ? `${edu.degree} in ${edu.branch || 'N/A'}` : edu.level || 'N/A'} - ${edu.board_university || 'N/A'}
            </div>
            <div class="text-sm text-slate-500">Year: ${edu.year || 'N/A'} | Score: ${edu.percentage_cgpa || 'N/A'}</div>
        </div>
    `).join('');
}

function populateSkillsResume() {
    const container = document.getElementById('skillsResumeContainer');
    
    if (!container) return;
    
    if (!Array.isArray(profileData.skills) || profileData.skills.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic">No skills added</p>';
        return;
    }
    
    // Group skills by category
    const grouped = {};
    profileData.skills.forEach(skill => {
        const category = skill.category || 'Other';
        if (!grouped[category]) grouped[category] = [];
        grouped[category].push(skill);
    });
    
    container.innerHTML = Object.entries(grouped).map(([category, skills]) => `
        <div class="mb-4">
            <div class="text-sm font-semibold text-slate-600 mb-2">${category}</div>
            <div class="flex flex-wrap gap-2">
                ${skills.map(skill => `
                    <span class="skill-tag" title="${skill.proficiency || 'N/A'}">
                        ${skill.name || 'Unnamed Skill'}
                        <span class="text-xs opacity-75">(${skill.proficiency || 'N/A'})</span>
                    </span>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function populateExperienceResume() {
    const container = document.getElementById('experienceResumeContainer');
    
    if (!container) return;
    
    if (!Array.isArray(profileData.experience) || profileData.experience.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic">No experience added yet</p>';
        toggleSection('experienceSection', false);
        return;
    }
    
    toggleSection('experienceSection', true);
    container.innerHTML = profileData.experience.map(exp => `
        <div class="resume-item mb-4">
            <div class="flex justify-between">
                <div class="font-semibold text-slate-800">${exp.role || 'N/A'}</div>
                <div class="text-sm text-slate-500">${exp.start_date || 'N/A'} - ${exp.is_current ? 'Present' : exp.end_date || 'N/A'}</div>
            </div>
            <div class="text-slate-600">${exp.company || 'N/A'}${exp.location ? ` • ${exp.location}` : ''}</div>
            <div class="text-sm text-slate-700 mt-2 whitespace-pre-wrap">${exp.description || 'No description provided'}</div>
        </div>
    `).join('');
}

function populateProjectsResume() {
    const container = document.getElementById('projectsResumeContainer');
    
    if (!container) return;
    
    if (!Array.isArray(profileData.projects) || profileData.projects.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic">No projects added yet</p>';
        toggleSection('projectsSection', false);
        return;
    }
    
    toggleSection('projectsSection', true);
    container.innerHTML = profileData.projects.map(proj => {
        // Handle tech_stack - it's always an array after sanitization
        let techStackDisplay = '';
        if (Array.isArray(proj.tech_stack)) {
            techStackDisplay = proj.tech_stack.join(', ');
        } else {
            techStackDisplay = 'N/A';
        }
        
        return `
            <div class="resume-item mb-4">
                <div class="font-semibold text-slate-800">${proj.title || 'Untitled Project'}</div>
                <div class="text-sm text-slate-600 mb-2">${techStackDisplay}</div>
                <div class="text-sm text-slate-700 whitespace-pre-wrap">${proj.description || 'No description provided'}</div>
                ${proj.link || proj.github_link ? `
                    <div class="flex gap-2 mt-2">
                        ${proj.link ? `<a href="${proj.link}" target="_blank" class="text-blue-600 text-sm hover:underline"><i class="fas fa-external-link-alt"></i> Live Demo</a>` : ''}
                        ${proj.github_link ? `<a href="${proj.github_link}" target="_blank" class="text-blue-600 text-sm hover:underline"><i class="fab fa-github"></i> GitHub</a>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function populateCertificationsResume() {
    const container = document.getElementById('certificationsResumeContainer');
    
    if (!container) return;
    
    if (!Array.isArray(profileData.certifications) || profileData.certifications.length === 0) {
        container.innerHTML = '<p class="text-slate-500 italic">No certifications added yet</p>';
        toggleSection('certificationsSection', false);
        return;
    }
    
    toggleSection('certificationsSection', true);
    container.innerHTML = profileData.certifications.map(cert => `
        <div class="resume-item mb-4">
            <div class="font-semibold text-slate-800">${cert.name || 'Unnamed Certification'}</div>
            <div class="text-slate-600">${cert.issuer || 'N/A'} • ${cert.issue_date || 'N/A'}</div>
            ${cert.credential_id ? `<div class="text-sm text-slate-500">Credential ID: ${cert.credential_id}</div>` : ''}
            ${cert.credential_url ? `<a href="${cert.credential_url}" target="_blank" class="text-blue-600 text-sm hover:underline"><i class="fas fa-external-link-alt"></i> Verify</a>` : ''}
        </div>
    `).join('');
}

function populateLinks() {
    const container = document.getElementById('profileLinks');
    
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!profileData.links || typeof profileData.links !== 'object') {
        container.innerHTML = '<p class="text-slate-500 italic">No links added</p>';
        toggleSection('linksSection', false);
        return;
    }
    
    const links = [
        { url: profileData.links.linkedin, icon: 'fab fa-linkedin', label: 'LinkedIn', color: 'bg-blue-50 text-blue-600' },
        { url: profileData.links.github, icon: 'fab fa-github', label: 'GitHub', color: 'bg-slate-50 text-slate-700' },
        { url: profileData.links.portfolio, icon: 'fas fa-globe', label: 'Portfolio', color: 'bg-purple-50 text-purple-600' },
        { url: profileData.links.resume_link, icon: 'fas fa-file-pdf', label: 'Resume', color: 'bg-red-50 text-red-600' },
        { url: profileData.links.twitter, icon: 'fab fa-twitter', label: 'Twitter', color: 'bg-sky-50 text-sky-600' },
        { url: profileData.links.leetcode, icon: 'fas fa-code', label: 'LeetCode', color: 'bg-orange-50 text-orange-600' }
    ];
    
    let hasLinks = false;
    
    links.forEach(link => {
        if (link.url && link.url.trim()) {
            hasLinks = true;
            const a = document.createElement('a');
            a.href = link.url;
            a.target = '_blank';
            a.className = `link-button ${link.color}`;
            a.innerHTML = `<i class="${link.icon}"></i> ${link.label}`;
            container.appendChild(a);
        }
    });
    
    if (!hasLinks) {
        container.innerHTML = '<p class="text-slate-500 italic">No links added</p>';
    }
    
    toggleSection('linksSection', hasLinks);
}

function populatePreferencesResume() {
    if (!profileData.preferences || typeof profileData.preferences !== 'object') {
        profileData.preferences = {};
    }
    
    const pref = profileData.preferences;
    
    // Helper function to safely get array values
    const getArrayDisplay = (arr) => {
        if (Array.isArray(arr) && arr.length > 0) {
            return arr.join(', ');
        }
        return '-';
    };
    
    const employmentTypeEl = document.getElementById('profileEmploymentType');
    const workModeEl = document.getElementById('profileWorkMode');
    const rolesEl = document.getElementById('profileRoles');
    const industriesEl = document.getElementById('profileIndustries');
    const salaryEl = document.getElementById('profileSalary');
    const relocateEl = document.getElementById('profileRelocate');
    const locationsEl = document.getElementById('profileLocations');
    
    if (employmentTypeEl) employmentTypeEl.textContent = getArrayDisplay(pref.employment_type);
    if (workModeEl) workModeEl.textContent = getArrayDisplay(pref.work_mode);
    if (rolesEl) rolesEl.textContent = pref.preferred_roles || '-';
    if (industriesEl) industriesEl.textContent = pref.preferred_industries || '-';
    if (salaryEl) salaryEl.textContent = pref.expected_salary || '-';
    if (relocateEl) relocateEl.textContent = pref.willing_to_relocate || '-';
    if (locationsEl) locationsEl.textContent = pref.preferred_locations || '-';
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