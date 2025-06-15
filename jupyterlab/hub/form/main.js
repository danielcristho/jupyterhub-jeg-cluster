// Configuration
const API_URL = "http://192.168.122.1:15002";
let profiles = [];
let nodes = [];
let selectedProfile = null;
let selectedNodes = [];

// Initialize
document.addEventListener('DOMContentLoaded', init);

async function init() {
    await checkAPI();
    await Promise.all([loadProfiles(), loadNodes()]);
    setupListeners();

    // Auto-select first profile
    setTimeout(() => {
        const firstProfile = document.querySelector('.profile-card');
        if (firstProfile) {
            firstProfile.click();
        }
    }, 100);
}

async function checkAPI() {
    const statusBar = document.getElementById('status-bar');
    try {
        const resp = await fetch(`${API_URL}/health-check`);
        if (resp.ok) {
            const data = await resp.json();
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
        // Use fallback data
        profiles = getFallbackProfiles();
        nodes = [];
    }
}

function getFallbackProfiles() {
    return [
        {
            id: 1,
            name: 'single-cpu',
            description: 'Single node with CPU only',
            min_nodes: 1,
            max_nodes: 1,
            cpu_requirement: 2,
            ram_requirement: 2,
            gpu_required: false
        },
        {
            id: 2,
            name: 'single-gpu',
            description: 'Single node with GPU acceleration',
            min_nodes: 1,
            max_nodes: 1,
            cpu_requirement: 2,
            ram_requirement: 2,
            gpu_required: true
        },
        {
            id: 3,
            name: 'multi-cpu',
            description: 'Multiple nodes with CPU only',
            min_nodes: 2,
            max_nodes: 4,
            cpu_requirement: 2,
            ram_requirement: 2,
            gpu_required: false
        },
        {
            id: 4,
            name: 'multi-gpu',
            description: 'Multiple nodes with GPU acceleration',
            min_nodes: 2,
            max_nodes: 4,
            cpu_requirement: 2,
            ram_requirement: 2,
            gpu_required: true
        }
    ];
}

async function loadProfiles() {
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
        profiles = getFallbackProfiles();
        renderProfiles();
    }
}

function renderProfiles() {
    const grid = document.getElementById('profile-grid');
    if (!grid) return;

    grid.innerHTML = '';

    profiles.forEach(profile => {
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.onclick = () => selectProfile(profile);

        const isMultiNode = profile.max_nodes > 1;
        const isGPU = profile.gpu_required;

        const displayName = profile.name
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');

        card.innerHTML = `
            <input type="radio" name="profile" value="${profile.id}">
            <div class="profile-header">
                <div class="profile-name">
                    ${displayName}
                </div>
            </div>
            <div class="profile-desc">${profile.description}</div>
            <div class="profile-specs">
                <div class="spec-item">
                    <span>${profile.cpu_requirement || 2} CPU cores</span>
                </div>
                <div class="spec-item">
                    <span>${profile.ram_requirement || 4} GB RAM</span>
                </div>
                <div class="spec-item">
                    <span>${isMultiNode ? `${profile.min_nodes}-${profile.max_nodes} nodes` : '1 node'}</span>
                </div>
                ${isGPU ? '<div class="spec-item"><span>GPU enabled</span></div>' : ''}
            </div>
        `;

        grid.appendChild(card);
    });
}

async function loadNodes() {
    try {
        const resp = await fetch(`${API_URL}/available-nodes`);
        if (resp.ok) {
            const data = await resp.json();
            nodes = data.all_available_nodes || [];
        }
    } catch (e) {
        console.log('No nodes available');
        nodes = [];
    }
}

async function selectProfile(profile) {
    selectedProfile = profile;

    // Update UI
    document.querySelectorAll('.profile-card').forEach(card => {
        card.classList.remove('selected');
    });
    event.currentTarget.classList.add('selected');

    // Update hidden fields
    document.getElementById('profile_id').value = profile.id;
    document.getElementById('profile_name').value = profile.name;

    // Update multi-node option
    const multiToggle = document.getElementById('multi-toggle');
    if (profile.max_nodes > 1) {
        multiToggle.style.display = 'block';
    } else {
        multiToggle.style.display = 'none';
        document.getElementById('single').checked = true;
        document.getElementById('multi-config').classList.add('hidden');
    }

    // Update image for GPU profiles
    if (profile.gpu_required) {
        document.getElementById('image').value = 'danielcristh0/jupyterlab:gpu';
    } else {
        document.getElementById('image').value = 'danielcristh0/jupyterlab:cpu';
    }
    
    // CRITICAL FIX: Log the selected image for debugging
    const selectedImage = document.getElementById('image').value;
    console.log('[DEBUG] Profile selected, image set to:', selectedImage);

    // Load and display nodes
    await displayNodes();
}

async function displayNodes() {
    const nodeList = document.getElementById('node-list');
    if (!nodeList) return;

    const isMulti = document.getElementById('multi').checked;
    const numNodes = isMulti ? parseInt(document.getElementById('num_nodes').value) : 1;

    // Show loading
    nodeList.innerHTML = '<div class="loading"><span class="spinner"></span>Selecting best nodes...</div>';

    try {
        // Request nodes from API
        const resp = await fetch(`${API_URL}/select-nodes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_id: selectedProfile.id,
                num_nodes: numNodes,
                user_id: 'jupyterhub-user'
            })
        });

        if (resp.ok) {
            const data = await resp.json();
            selectedNodes = data.selected_nodes || [];
            renderNodes(selectedNodes);
            updateSummary();
        } else {
            const errorData = await resp.json();
            throw new Error(errorData.error || 'Failed to select nodes');
        }
    } catch (e) {
        console.error('Error selecting nodes:', e);
        // Fallback: show available nodes
        if (nodes.length > 0) {
            const suitable = nodes.filter(n => nodeMatchesProfile(n, selectedProfile));
            if (suitable.length > 0) {
                selectedNodes = suitable.slice(0, numNodes);
                renderNodes(selectedNodes);
                updateSummary();
            } else {
                nodeList.innerHTML = '<div class="loading">No suitable nodes available for this profile</div>';
            }
        } else {
            nodeList.innerHTML = '<div class="loading">No nodes available</div>';
        }
    }
}

function nodeMatchesProfile(node, profile) {
    if (!node || !profile) return false;
    if (profile.cpu_requirement && node.cpu < profile.cpu_requirement) return false;
    if (profile.ram_requirement && node.ram_gb < profile.ram_requirement) return false;
    if (profile.gpu_required && !node.has_gpu) return false;
    // Check usage
    if (node.cpu_usage_percent > (profile.max_cpu_usage || 80)) return false;
    if (node.memory_usage_percent > (profile.max_memory_usage || 85)) return false;
    return true;
}

function renderNodes(nodesList) {
    const nodeList = document.getElementById('node-list');
    if (!nodeList || !nodesList) return;

    nodeList.innerHTML = '';

    nodesList.forEach((node, index) => {
        const cpu = node.cpu_usage_percent || 0;
        const mem = node.memory_usage_percent || 0;

        let status = 'healthy';
        let statusText = 'Available';
        if (cpu > 80 || mem > 80) {
            status = 'overloaded';
            statusText = 'High Load';
        } else if (cpu > 60 || mem > 60) {
            status = 'busy';
            statusText = 'Moderate Load';
        }

        const nodeDiv = document.createElement('div');
        nodeDiv.className = `node-item ${index === 0 ? 'selected' : ''}`;

        nodeDiv.innerHTML = `
            <div class="node-header">
                <div class="node-name">
                    ${node.hostname}
                    ${index === 0 ? '<small style="color: #666; font-weight: normal;">(Primary)</small>' : ''}
                </div>
                <div class="node-status ${status}">
                    <span style="font-size: 10px;">●</span> ${statusText}
                </div>
            </div>

            <div class="node-specs">
                <div class="node-spec"><strong>IP:</strong> ${node.ip}</div>
                <div class="node-spec"><strong>CPU:</strong> ${node.cpu} cores</div>
                <div class="node-spec"><strong>Memory:</strong> ${node.ram_gb} GB</div>
                <div class="node-spec"><strong>Containers:</strong> ${node.total_containers || 0} active</div>
            </div>

            ${node.has_gpu ? `
                <div class="gpu-info">
                    <span>GPU: </span>
                    <span>${node.gpu && node.gpu[0] ? node.gpu[0].name : 'GPU Available'}</span>
                </div>
            ` : ''}

            <div class="node-metrics">
                <div class="metric">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-bar">
                        <div class="metric-fill ${cpu > 80 ? 'high' : cpu > 60 ? 'medium' : ''}"
                                style="width: ${cpu}%"></div>
                    </div>
                    <div class="metric-value">${cpu.toFixed(1)}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-bar">
                        <div class="metric-fill ${mem > 80 ? 'high' : mem > 60 ? 'medium' : ''}"
                                style="width: ${mem}%"></div>
                    </div>
                    <div class="metric-value">${mem.toFixed(1)}%</div>
                </div>
            </div>
        `;

        nodeList.appendChild(nodeDiv);
    });

    // CRITICAL FIX: Convert selectedNodes to JSON string before setting
    console.log('[DEBUG] selectedNodes before JSON.stringify:', selectedNodes);
    const selectedNodesJson = JSON.stringify(selectedNodes);
    console.log('[DEBUG] selectedNodes JSON string:', selectedNodesJson);
    
    document.getElementById('selected_nodes').value = selectedNodesJson;
    document.getElementById('node_count_final').value = selectedNodes.length;
    if (selectedNodes.length > 0) {
        document.getElementById('primary_node').value = selectedNodes[0].hostname;
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
    const avgCPUUsage = (selectedNodes.reduce((sum, n) => sum + (n.cpu_usage_percent || 0), 0) / selectedNodes.length).toFixed(1);
    const avgMemUsage = (selectedNodes.reduce((sum, n) => sum + (n.memory_usage_percent || 0), 0) / selectedNodes.length).toFixed(1);

    let summary = `<strong>Selected ${selectedNodes.length} node${selectedNodes.length > 1 ? 's' : ''}:</strong><br>`;
    summary += `• Total Resources: ${totalCPU} CPU cores, ${totalRAM} GB RAM`;
    if (hasGPU) {
        const gpuNodes = selectedNodes.filter(n => n.has_gpu);
        summary += `, ${gpuNodes.length} GPU${gpuNodes.length > 1 ? 's' : ''}`;
    }
    summary += `<br>• Average Load: CPU ${avgCPUUsage}%, Memory ${avgMemUsage}%`;

    if (selectedNodes.length > 1) {
        summary += `<br>• Primary Node: ${selectedNodes[0].hostname}`;
        summary += `<br>• Worker Nodes: ${selectedNodes.slice(1).map(n => n.hostname).join(', ')}`;
    }

    summaryContent.innerHTML = summary;
    summaryBox.classList.remove('hidden');
}

function setupListeners() {
    // Node count toggle
    document.querySelectorAll('input[name="node_count"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const multiConfig = document.getElementById('multi-config');
            if (this.value === 'multi') {
                multiConfig.classList.remove('hidden');
            } else {
                multiConfig.classList.add('hidden');
            }
            if (selectedProfile) {
                displayNodes();
            }
        });
    });

    // Number of nodes change
    const numNodesSelect = document.getElementById('num_nodes');
    if (numNodesSelect) {
        numNodesSelect.addEventListener('change', function() {
            if (selectedProfile) {
                displayNodes();
            }
        });
    }

    // Image change
    const imageSelect = document.getElementById('image');
    if (imageSelect) {
        imageSelect.addEventListener('change', function() {
            console.log('Image changed to:', this.value);
        });
    }
}

// Auto-refresh nodes every 30 seconds
setInterval(async function() {
    if (selectedProfile) {
        await loadNodes();
        // Only update display if user hasn't manually selected
        if (document.querySelector('.node-item.manual-select') === null) {
            // await displayNodes();
        }
    }
}, 30000);

document.querySelector("form").addEventListener("submit", function (e) {
    if (!selectedProfile || selectedNodes.length === 0) {
        e.preventDefault();
        alert("Please select a profile and wait for node selection before launching.");
        return;
    }
    
    // Additional validation before submit
    const selectedNodesValue = document.getElementById('selected_nodes').value;
    console.log('[SUBMIT] Final selected_nodes value:', selectedNodesValue);
    
    if (!selectedNodesValue || selectedNodesValue === '[]') {
        e.preventDefault();
        alert("No nodes selected. Please try selecting a profile again.");
        return;
    }
    
    // CRITICAL FIX: Validate image selection
    const imageValue = document.getElementById('image').value;
    console.log('[SUBMIT] Final image value:', imageValue);
    
    if (!imageValue || imageValue.trim() === '') {
        e.preventDefault();
        alert("No image selected. Please select an image.");
        return;
    }
    
    // Final form data logging for debugging
    console.log('[SUBMIT] Form data summary:');
    console.log('- Profile ID:', document.getElementById('profile_id').value);
    console.log('- Profile Name:', document.getElementById('profile_name').value);
    console.log('- Image:', imageValue);
    console.log('- Selected Nodes:', selectedNodesValue);
    console.log('- Primary Node:', document.getElementById('primary_node').value);
});