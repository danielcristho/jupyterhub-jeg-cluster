const API_URL = "http://192.168.122.1:15002";
let profiles = [];
let nodes = [];
let selectedProfile = null;
let selectedNodes = [];

// =================================
// Inisialisasi
// =================================
document.addEventListener('DOMContentLoaded', init);

async function init() {
    await checkAPI();
    await Promise.all([loadProfiles(), loadNodes()]);
    setupListeners();

    // Pilih profil pertama secara otomatis untuk memulai
    setTimeout(() => {
        const firstProfile = document.querySelector('.profile-card');
        if (firstProfile) {
            firstProfile.click();
        }
    }, 100);
}

// =================================
// Interaksi dengan Discovery API
// =================================
async function checkAPI() {
    const statusBar = document.getElementById('status-bar');
    try {
        const resp = await fetch(`${API_URL}/health-check`);
        if (resp.ok) {
            statusBar.innerHTML = `
                <div class="status-item success">
                    <span class="status-icon">✓</span>
                    <span>Discovery Service Connected</span>
                </div>
            `;
        } else {
            throw new Error('API not responding');
        }
    } catch (e) {
        statusBar.innerHTML = `
            <div class="status-item warning">
                <span class="status-icon">⚠️</span>
                <span>Offline Mode - Using default configuration</span>
            </div>
        `;
        profiles = getFallbackProfiles();
        nodes = [];
    }
}

async function loadProfiles() {
    const grid = document.getElementById('profile-grid');
    try {
        const resp = await fetch(`${API_URL}/profiles`);
        if (resp.ok) {
            const data = await resp.json();
            profiles = data.profiles || [];
            renderProfiles();
        } else {
            throw new Error('Failed to load profiles');
        }
    } catch (e) {
        console.error('Error loading profiles:', e);
        grid.innerHTML = '<div class="loading">Failed to load profiles. Using fallbacks.</div>';
        profiles = getFallbackProfiles();
        renderProfiles();
    }
}

async function loadNodes() {
    try {
        const resp = await fetch(`${API_URL}/available-nodes`);
        if (resp.ok) {
            const data = await resp.json();
            nodes = data.all_available_nodes || [];
        }
    } catch (e) {
        console.log('Could not fetch available nodes:', e);
        nodes = [];
    }
}

// =================================
// Rendering & Tampilan UI
// =================================
function renderProfiles() {
    const grid = document.getElementById('profile-grid');
    if (!grid) return;
    grid.innerHTML = '';

    profiles.forEach(profile => {
        const card = document.createElement('div');
        card.className = 'profile-card';
        // Menggunakan event.currentTarget di selectProfile, jadi perlu event
        card.onclick = (event) => selectProfile(profile, event);

        const displayName = profile.name.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

        card.innerHTML = `
            <div class="profile-header"><div class="profile-name">${displayName}</div></div>
            <div class="profile-desc">${profile.description}</div>
            <div class="profile-specs">
                <div class="spec-item"><span>${profile.cpu_requirement || 2} CPU cores</span></div>
                <div class="spec-item"><span>${profile.ram_requirement || 4} GB RAM</span></div>
                <div class="spec-item"><span>${profile.max_nodes > 1 ? `${profile.min_nodes}-${profile.max_nodes} nodes` : '1 node'}</span></div>
                ${profile.gpu_required ? '<div class="spec-item"><span>GPU enabled</span></div>' : ''}
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderNodes(nodesList) {
    const nodeList = document.getElementById('node-list');
    if (!nodeList || !nodesList) return;
    nodeList.innerHTML = '';

    if (nodesList.length === 0) {
        nodeList.innerHTML = '<div class="loading">No suitable nodes could be selected.</div>';
        return;
    }

    nodesList.forEach((node, index) => {
        const cpu = node.cpu_usage_percent || 0;
        const mem = node.memory_usage_percent || 0;
        let status = 'healthy';
        let statusText = 'Available';
        if (cpu > 80 || mem > 80) { status = 'overloaded'; statusText = 'High Load'; } 
        else if (cpu > 60 || mem > 60) { status = 'busy'; statusText = 'Moderate Load'; }

        const nodeDiv = document.createElement('div');
        nodeDiv.className = `node-item ${index === 0 ? 'selected' : ''}`;
        nodeDiv.innerHTML = `
            <div class="node-header">
                <div class="node-name">${node.hostname} ${index === 0 ? '<small style="color: #666; font-weight: normal;">(Primary)</small>' : ''}</div>
                <div class="node-status ${status}"><span style="font-size: 10px;">●</span> ${statusText}</div>
            </div>
            <div class="node-specs">
                <div class="node-spec"><strong>IP:</strong> ${node.ip}</div>
                <div class="node-spec"><strong>CPU:</strong> ${node.cpu} cores</div>
                <div class="node-spec"><strong>Memory:</strong> ${node.ram_gb} GB</div>
                <div class="node-spec"><strong>Containers:</strong> ${node.total_containers || 0} active</div>
            </div>
            ${node.has_gpu ? `<div class="gpu-info"><span>GPU: </span><span>${node.gpu && node.gpu[0] ? node.gpu[0].name : 'GPU Available'}</span></div>` : ''}
            <div class="node-metrics">
                <div class="metric"><div class="metric-label">CPU Usage</div><div class="metric-bar"><div class="metric-fill ${cpu > 80 ? 'high' : cpu > 60 ? 'medium' : ''}" style="width: ${cpu}%"></div></div><div class="metric-value">${cpu.toFixed(1)}%</div></div>
                <div class="metric"><div class="metric-label">Memory Usage</div><div class="metric-bar"><div class="metric-fill ${mem > 80 ? 'high' : mem > 60 ? 'medium' : ''}" style="width: ${mem}%"></div></div><div class="metric-value">${mem.toFixed(1)}%</div></div>
            </div>
        `;
        nodeList.appendChild(nodeDiv);
    });

    document.getElementById('selected_nodes').value = JSON.stringify(nodesList);
    document.getElementById('node_count_final').value = nodesList.length;
    if (nodesList.length > 0) {
        document.getElementById('primary_node').value = nodesList[0].hostname;
    }
}


// =================================
// Core logic & State Management
// =================================
async function selectProfile(profile, event) {
    selectedProfile = profile;

    document.querySelectorAll('.profile-card').forEach(card => card.classList.remove('selected'));
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('selected');
    }

    document.getElementById('profile_id').value = profile.id;
    document.getElementById('profile_name').value = profile.name;

    const multiToggle = document.getElementById('multi-toggle');
    multiToggle.style.display = profile.max_nodes > 1 ? 'block' : 'none';
    if (profile.max_nodes <= 1) {
        document.getElementById('single').checked = true;
        document.getElementById('multi-config').classList.add('hidden');
    }

    document.getElementById('image').value = profile.gpu_required ? 'danielcristh0/jupyterlab:gpu' : 'danielcristh0/jupyterlab:cpu';
    
    await displayNodes();
}

async function displayNodes() {
    const nodeList = document.getElementById('node-list');
    if (!nodeList || !selectedProfile) return;

    const isMulti = document.getElementById('multi').checked;
    const numNodes = isMulti ? parseInt(document.getElementById('num_nodes').value) : 1;

    nodeList.innerHTML = '<div class="loading"><span class="spinner"></span>Selecting best nodes...</div>';

    try {
        const resp = await fetch(`${API_URL}/select-nodes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_id: selectedProfile.id,
                num_nodes: numNodes,
                user_id: 'jupyterhub-user'
            })
        });

        if (!resp.ok) {
            const errorData = await resp.json().catch(() => ({ error: 'Failed to select nodes' }));
            throw new Error(errorData.error);
        }
        
        const data = await resp.json();
        selectedNodes = data.selected_nodes || [];
        renderNodes(selectedNodes);
        updateSummary();

    } catch (e) {
        console.error('Error selecting nodes:', e);
        nodeList.innerHTML = `<div class="loading">Error selecting nodes: ${e.message}</div>`;
        selectedNodes = []; // Reset selected nodes on error
        updateSummary();
    }
}

function updateSummary() {
    const summaryBox = document.getElementById('selection-summary');
    const summaryContent = document.getElementById('summary-content');
    if (!summaryBox || !summaryContent) return;

    if (selectedNodes.length === 0) {
        summaryBox.classList.add('hidden');
        return;
    }

    const totalCPU = selectedNodes.reduce((sum, n) => sum + (n.cpu || 0), 0);
    const totalRAM = selectedNodes.reduce((sum, n) => sum + (n.ram_gb || 0), 0);
    const hasGPU = selectedNodes.some(n => n.has_gpu);

    let summary = `<strong>Selected ${selectedNodes.length} node${selectedNodes.length > 1 ? 's' : ''}:</strong><br>`;
    summary += `• Total Resources: ${totalCPU} CPU cores, ${totalRAM} GB RAM`;
    if (hasGPU) summary += `, ${selectedNodes.filter(n => n.has_gpu).length} GPU(s)`;
    if (selectedNodes.length > 1) {
        summary += `<br>• Primary: ${selectedNodes[0].hostname}, Workers: ${selectedNodes.slice(1).map(n => n.hostname).join(', ')}`;
    }
    summaryContent.innerHTML = summary;
    summaryBox.classList.remove('hidden');
}

function getFallbackProfiles() {
    // Data cadangan jika API tidak bisa dijangkau
    return [
        { id: 1, name: 'single-cpu', description: 'Single node with CPU only', min_nodes: 1, max_nodes: 1, cpu_requirement: 2, ram_requirement: 2, gpu_required: false },
        { id: 2, name: 'single-gpu', description: 'Single node with GPU acceleration', min_nodes: 1, max_nodes: 1, cpu_requirement: 2, ram_requirement: 2, gpu_required: true },
        { id: 3, name: 'multi-cpu', description: 'Multiple nodes with CPU only', min_nodes: 2, max_nodes: 4, cpu_requirement: 2, ram_requirement: 2, gpu_required: false },
        { id: 4, name: 'multi-gpu', description: 'Multiple nodes with GPU acceleration', min_nodes: 2, max_nodes: 4, cpu_requirement: 2, ram_requirement: 2, gpu_required: true }
    ];
}


// =================================
// Event Listeners
// =================================
function setupListeners() {
    document.querySelectorAll('input[name="node_count"]').forEach(radio => {
        radio.addEventListener('change', function() {
            document.getElementById('multi-config').classList.toggle('hidden', this.value !== 'multi');
            if (selectedProfile) displayNodes();
        });
    });

    document.getElementById('num_nodes')?.addEventListener('change', () => {
        if (selectedProfile) displayNodes();
    });
    
    document.getElementById('image')?.addEventListener('change', function() {
        console.log('Image selection changed to:', this.value);
    });

    const nextButton = document.getElementById('next-button');
    if (nextButton) {
        nextButton.addEventListener('click', function() {
            if (!selectedProfile || selectedNodes.length === 0) {
                alert("Please select a profile and wait for node selection before proceeding.");
                return;
            }

            const finalConfig = {
                profile_id: document.getElementById('profile_id').value,
                profile_name: document.getElementById('profile_name').value,
                image: document.getElementById('image').value,
                node_count: document.getElementById('node_count_final').value,
                primary_node: document.getElementById('primary_node').value,
                selected_nodes: selectedNodes 
            };
            
            console.log('[NEXT_BUTTON] Saving config to localStorage:', finalConfig);
            localStorage.setItem("jupyterhub_spawn_config", JSON.stringify(finalConfig));
            window.location.href = '/hub/form/control.html';
        });
    }
}

setInterval(async function() {
    if (selectedProfile) {
        await loadNodes();
    }
}, 30000);