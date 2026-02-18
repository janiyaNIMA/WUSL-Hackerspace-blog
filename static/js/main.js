document.addEventListener('DOMContentLoaded', () => {
    // Shared initialization
    fetchReminders();
    initMobileMenu();
    initProfilePopup();
});

function initProfilePopup() {
    const trigger = document.getElementById('profile-trigger');
    const popup = document.getElementById('profile-popup');
    const overlay = document.getElementById('profile-overlay');

    if (trigger && popup) {
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = popup.classList.toggle('active');
            if (overlay) overlay.classList.toggle('active');

            // Prevent scrolling on mobile when popup is open
            if (window.innerWidth <= 860) {
                document.body.style.overflow = isActive ? 'hidden' : '';
            }
        });

        const closePopup = () => {
            popup.classList.remove('active');
            if (overlay) overlay.classList.remove('active');
            document.body.style.overflow = '';
        };

        document.addEventListener('click', (e) => {
            if (!popup.contains(e.target) && !trigger.contains(e.target)) {
                closePopup();
            }
        });

        if (overlay) {
            overlay.addEventListener('click', closePopup);
        }
    }
}

function initMobileMenu() {
    const toggle = document.getElementById('menu-toggle');
    const nav = document.getElementById('top-nav');

    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            nav.classList.toggle('show');
            toggle.classList.toggle('active');
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!nav.contains(e.target) && !toggle.contains(e.target)) {
                nav.classList.remove('show');
                toggle.classList.remove('active');
            }
        });
    }
}

async function fetchMembers() {
    const grid = document.getElementById('members-grid');
    if (!grid) return;

    try {
        const response = await fetch('/api/members');
        const members = await response.json();

        grid.innerHTML = members.map(member => `
            <div class="member-card">
                <img src="${member.avatar}" alt="${member.name}" class="member-avatar">
                <div class="member-info">
                    <h4>${member.name}</h4>
                    <p>${member.role}</p>
                </div>
            </div>
        `).join('');
    } catch (error) {
        grid.innerHTML = '<p>Error loading members.</p>';
    }
}

// Helper to render modular content blocks
function renderContentBlocks(blocksInput) {
    if (!blocksInput) return '';
    let blocks = blocksInput;

    // Support both JSON string (legacy/direct) and Array (structured API)
    if (typeof blocksInput === 'string') {
        try {
            blocks = JSON.parse(blocksInput);
        } catch (e) {
            return `<p>${blocksInput}</p>`;
        }
    }

    if (!Array.isArray(blocks)) return '';

    return blocks.map(block => {
        if (block.type === 'text') {
            if (block.sub_type === 'heading') return `<h5 class="block-heading">${block.value}</h5>`;
            return `<p class="block-paragraph">${block.value}</p>`;
        } else if (block.type === 'media') {
            if (block.sub_type === 'image') {
                return `<div class="block-media-container"><img src="${block.value}" class="block-img"></div>`;
            }
            if (block.sub_type === 'video') {
                return `<div class="block-media-container"><iframe src="${block.value}" class="block-video" frameborder="0" allowfullscreen></iframe></div>`;
            }
        }
        return '';
    }).join('');
}

// Helper to get thumbnail from blocks if missing
function getThumbnail(item) {
    if (item.thumbnail && item.thumbnail.trim() !== "") return item.thumbnail;

    const blocks = item.blocks || [];
    const firstImg = blocks.find(b => b.type === 'media' && b.sub_type === 'image');
    return firstImg ? firstImg.value : '/static/img/logo.png';
}

async function fetchProjects() {
    const grid = document.getElementById('content-grid');
    const title = document.getElementById('section-title');
    if (!grid || !title) return;

    title.textContent = "Featured Projects";
    grid.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();

        grid.innerHTML = projects.map(project => `
            <div class="project-card">
                <div class="project-img-wrapper">
                    <img src="${getThumbnail(project)}" alt="${project.title}" class="project-thumbnail">
                </div>
                <div class="project-info">
                    <h4 style="color: ${project.color || 'var(--dark-brown)'}">${project.title}</h4>
                    <div class="content-blocks-preview">
                        ${renderContentBlocks(project.blocks)}
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        grid.innerHTML = '<p>Error loading projects.</p>';
    }
}

async function fetchArticles() {
    const grid = document.getElementById('content-grid');
    const title = document.getElementById('section-title');
    title.textContent = "Latest News";
    grid.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const response = await fetch('/api/articles');
        const articles = await response.json();

        grid.innerHTML = articles.map(article => `
            <div class="article-card">
                <div class="article-header">
                    <h4>${article.title}</h4>
                    <span class="article-date"><i class="fa-regular fa-calendar"></i> ${article.date}</span>
                </div>
                <div class="article-body">
                    ${renderContentBlocks(article.blocks)}
                </div>
                <div class="article-footer">
                    <span><i class="fa-solid fa-user-pen"></i> ${article.author}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        grid.innerHTML = '<p>Error loading articles.</p>';
    }
}

async function fetchProjectsOnNews() {
    const grid = document.getElementById('projects-grid');
    if (!grid) return;

    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();

        grid.innerHTML = projects.map(project => `
            <div class="project-card">
                <div class="project-img-wrapper">
                    <img src="${getThumbnail(project)}" alt="${project.title}" class="project-thumbnail">
                </div>
                <div class="project-info">
                    <h4 style="color: ${project.color || 'var(--dark-brown)'}">${project.title}</h4>
                    <div class="content-blocks-preview">
                        ${renderContentBlocks(project.blocks)}
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        grid.innerHTML = '<p>Error loading projects.</p>';
    }
}

async function fetchArticlesOnNews() {
    const grid = document.getElementById('articles-grid');
    if (!grid) return;

    try {
        const response = await fetch('/api/articles');
        const articles = await response.json();

        grid.innerHTML = articles.map(article => `
            <div class="article-card">
                <div class="article-header">
                    <h4>${article.title}</h4>
                    <span class="article-date"><i class="fa-regular fa-calendar"></i> ${article.date}</span>
                </div>
                <div class="article-body">
                    ${renderContentBlocks(article.blocks)}
                </div>
                <div class="article-footer">
                    <span><i class="fa-solid fa-user-pen"></i> ${article.author}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        grid.innerHTML = '<p>Error loading articles.</p>';
    }
}

async function fetchReminders() {
    const list = document.getElementById('reminder-list');

    try {
        const response = await fetch('/api/reminders');
        const reminders = await response.json();

        list.innerHTML = reminders.map(r => `
            <li class="reminder-item">${r.text}</li>
        `).join('');
    } catch (error) {
        list.innerHTML = '<li class="reminder-item">Error loading reminders</li>';
    }
}
