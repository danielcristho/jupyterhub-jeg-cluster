let availableProfiles = [];
let selectedProfile = null;
let availableNodes = [];
let allocatedNodes = [];
let currentStep = 1;

const DISCOVERY_API_URL = "http://127.0.0.1:15002";

window.onload = async function() {
  await checkApiStatus();
  await loadProfiles();
  await loadNodes();
};

async function checkApiStatus() {
  const statusDiv = document.getElementById("api-status");
  try {
    const res = await fetch(`${DISCOVERY_API_URL}/health-check`);
    const data = await res.json();
    statusDiv.innerHTML = `<div class='message message-success'>Discovery API Connected<br><small>${data.message}</small></div>`;
  } catch (e) {
    statusDiv.innerHTML = `<div class='message message-error'>Discovery API Unreachable<br><small>Please check your connection</small></div>`;
  }
}

async function loadProfiles() {
  try {
    const res = await fetch(`${DISCOVERY_API_URL}/api/profiles`);
    const data = await res.json();
    availableProfiles = data.profiles || [];
    renderProfiles();
  } catch (e) {
    console.error("Failed to load profiles:", e);
    // Fallback to default profiles
    availableProfiles = [
      {
        id: 1,
        name: "Single Node - Light",
        description: "Perfect for learning and basic data analysis",
        node_count: 1,
        cpu_requirement: 1.0,
        memory_requirement: 2.0,
        gpu_required: false
      },
      {
        id: 2,
        name: "Single Node - Standard",
        description: "Ideal for data science and machine learning",
        node_count: 1,
        cpu_requirement: 2.0,
        memory_requirement: 4.0,
        gpu_required: false
      },
      {
        id: 3,
        name: "Single Node - GPU",
        description: "High-performance computing with GPU acceleration",
        node_count: 1,
        cpu_requirement: 4.0,
        memory_requirement: 8.0,
        gpu_required: true
      },
      {
        id: 4,
        name: "Multi Node - Distributed",
        description: "Distributed computing across 3 nodes",
        node_count: 3,
        cpu_requirement: 2.0,
        memory_requirement: 4.0,
        gpu_required: false
      }
    ];
    renderProfiles();
  }
}

function renderProfiles() {
  const grid = document.getElementById("profile-grid");
  grid.innerHTML = "";

  availableProfiles.forEach(profile => {
    const card = document.createElement("div");
    card.className = "profile-card";
    card.onclick = () => selectProfile(profile.id);

    const badges = [];
    if (profile.gpu_required) badges.push('<span class="badge badge-gpu">GPU</span>');
    if (profile.node_count > 1) badges.push('<span class="badge badge-multi">' + profile.node_count + ' Nodes</span>');
    if (profile.cpu_requirement >= 4) badges.push('<span class="badge badge-premium">High Performance</span>');

    card.innerHTML = `
      <input type="radio" name="profile_id" value="${profile.id}" />
      <div class="profile-title">${profile.name}${badges.join('')}</div>
      <div class="profile-desc">${profile.description}</div>
      <div class="profile-specs">
        <div class="spec-item">
          <svg class="spec-icon" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
          </svg>
          ${profile.cpu_requirement} CPU cores
        </div>
        <div class="spec-item">
          <svg class="spec-icon" fill="currentColor" viewBox="0 0 20 20">
            <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
          </svg>
          ${profile.memory_requirement} GB RAM
        </div>
        <div class="spec-item">
          <svg class="spec-icon" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          ${profile.node_count} Node(s)
        </div>
        <div class="spec-item">
          <svg class="spec-icon" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"/>
          </svg>
          ${profile.gpu_required ? 'GPU Required' : 'CPU Only'}
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

function selectProfile(profileId) {
  selectedProfile = availableProfiles.find(p => p.id === profileId);

  // Update UI
  document.querySelectorAll('.profile-card').forEach(card => {
    card.classList.remove('selected');
  });
  event.currentTarget.classList.add('selected');

  // Update form
  document.getElementById('input-profile-id').value = profileId;
  document.querySelector(`input[value="${profileId}"]`).checked = true;
}

async function loadNodes() {
  try {
    const res = await fetch(`${DISCOVERY_API_URL}/available-nodes`);
    const data = await res.json();
    availableNodes = data.all_available_nodes || [];
  } catch (e) {
    console.error("Failed to load nodes:", e);
  }
}

function nextStep(step) {
  if (step === 2) {
    if (!selectedProfile) {
      alert("Please select a computing profile first.");
      return;
    }
    setupConfigurationStep();
  } else if (step === 3) {
    if (selectedProfile.node_count === 1) {
      const nodeInput = document.getElementById("input-node");
      if (!nodeInput.value) {
        alert("Please wait for node allocation or try again.");
        return;
      }
    }
    setupLaunchStep();
  }

  currentStep = step;
  updateStepNavigation();
  showStep(step);
}

function prevStep(step) {
  currentStep = step;
  updateStepNavigation();
  showStep(step);
}

function showStep(step) {
  document.querySelectorAll('.step-content').forEach(content => {
    content.classList.remove('active');
  });
  document.querySelector(`.step-content[data-step="${step}"]`).classList.add('active');
}

function updateStepNavigation() {
  document.querySelectorAll('.step').forEach((step, index) => {
    const stepNumber = index + 1;
    step.classList.remove('active', 'completed');

    if (stepNumber === currentStep) {
      step.classList.add('active');
    } else if (stepNumber < currentStep) {
      step.classList.add('completed');
    }
  });
}

async function setupConfigurationStep() {
  if (selectedProfile.node_count === 1) {
    // Single node configuration
    document.getElementById('single-node-config').classList.remove('hidden');
    document.getElementById('multi-node-config').classList.add('hidden');

    await setupSingleNodeConfig();
  } else {
    // Multi node configuration
    document.getElementById('single-node-config').classList.add('hidden');
    document.getElementById('multi-node-config').classList.remove('hidden');

    await setupMultiNodeConfig();
  }
}

async function setupSingleNodeConfig() {
  // Show cluster status
  const statusDiv = document.getElementById('cluster-status');
  const healthyNodes = availableNodes.filter(n => isNodeHealthy(n));
  const gpuNodes = availableNodes.filter(n => n.has_gpu);

  statusDiv.innerHTML = `
    <div class="message message-info">
      <strong>Cluster Status:</strong> ${healthyNodes.length}/${availableNodes.length} nodes available
      (${gpuNodes.length} GPU nodes)
    </div>
  `;

  // Auto-select optimal node
  await selectOptimalNode();
}

async function selectOptimalNode() {
  try {
    let endpoint = "/balanced-node";
    if (selectedProfile.gpu_required) {
      // For GPU profiles, we need nodes with GPU
      const gpuNodes = availableNodes.filter(n => n.has_gpu && isNodeHealthy(n));
      if (gpuNodes.length === 0) {
        document.getElementById('node-selection').innerHTML = `
          <div class="message message-error">
            No GPU nodes available for this profile. Please try again later or select a different profile.
          </div>
        `;
        return;
      }
    }

    const res = await fetch(`${DISCOVERY_API_URL}${endpoint}`);
    const data = await res.json();
    const selectedNode = data.selected_node;

    if (selectedNode) {
      updateSingleNodeSelection(selectedNode);
    }
  } catch (e) {
    console.error("Failed to select node:", e);
  }
}

function updateSingleNodeSelection(node) {
  const selectionDiv = document.getElementById('node-selection');
  const cpuUsage = parseFloat(node.cpu_usage_percent || 0).toFixed(1);
  const memUsage = parseFloat(node.memory_usage_percent || 0).toFixed(1);

  selectionDiv.innerHTML = `
    <div class="message message-success">
      <strong>Selected Node:</strong> ${node.hostname}<br>
      <strong>Resources:</strong> ${node.cpu} CPU cores, ${node.ram_gb} GB RAM<br>
      <strong>Current Usage:</strong> CPU ${cpuUsage}%, Memory ${memUsage}%<br>
      <strong>GPU:</strong> ${node.has_gpu ? (node.gpu?.length || 1) + ' GPU(s) available' : 'Not available'}<br>
      <small>IP: ${node.ip}</small>
    </div>
  `;

  // Update form fields
  document.getElementById('input-node').value = node.hostname;
  document.getElementById('input-node-ip').value = node.ip;
}

async function setupMultiNodeConfig() {
  // Show multi-node summary
  const summaryDiv = document.getElementById('multi-node-summary');
  summaryDiv.innerHTML = `
    <div class="message message-info">
      <strong>Multi-Node Setup:</strong> ${selectedProfile.node_count} nodes will be allocated<br>
      <strong>Total Resources:</strong> ${selectedProfile.node_count * selectedProfile.cpu_requirement} CPU cores,
      ${selectedProfile.node_count * selectedProfile.memory_requirement} GB RAM<br>
      <strong>Note:</strong> Multi-node distributed computing
    </div>
  `;

  // Allocate nodes
  await allocateMultipleNodes();
}

async function allocateMultipleNodes() {
  try {
    const sessionId = `jupyter-${Date.now()}-preview`;
    const payload = {
      session_id: sessionId,
      user_id: "preview-user",
      profile_id: selectedProfile.id
    };

    // For demo purposes, we'll simulate allocation
    // In real implementation, this would call the allocation API
    const suitableNodes = availableNodes
      .filter(n => isNodeHealthy(n))
      .slice(0, selectedProfile.node_count);

    allocatedNodes = suitableNodes;
    renderAllocatedNodes();

    // Update form with primary node
    if (allocatedNodes.length > 0) {
      document.getElementById('input-node').value = allocatedNodes[0].hostname;
      document.getElementById('input-node-ip').value = allocatedNodes[0].ip;

      const sessionConfig = {
        profile_id: selectedProfile.id,
        allocated_nodes: allocatedNodes.map(n => n.hostname),
        node_count: selectedProfile.node_count
      };
      document.getElementById('input-session-config').value = JSON.stringify(sessionConfig);
    }
  } catch (e) {
    console.error("Failed to allocate nodes:", e);
  }
}

function renderAllocatedNodes() {
  const nodesDiv = document.getElementById('allocated-nodes');
  nodesDiv.innerHTML = '';

  allocatedNodes.forEach((node, index) => {
    const nodeCard = document.createElement('div');
    nodeCard.className = 'node-card selected';

    const role = index === 0 ? 'Primary' : `Worker ${index}`;
    const cpuUsage = parseFloat(node.cpu_usage_percent || 0).toFixed(1);
    const memUsage = parseFloat(node.memory_usage_percent || 0).toFixed(1);

    nodeCard.innerHTML = `
      <div class="node-header">
        <div class="node-name">${node.hostname}</div>
        <div class="node-status status-healthy"></div>
      </div>
      <div class="node-stats">
        <strong>${role} Node</strong><br>
        CPU: ${cpuUsage}% of ${node.cpu} cores<br>
        Memory: ${memUsage}% of ${node.ram_gb} GB<br>
        IP: ${node.ip}
      </div>
    `;

    nodesDiv.appendChild(nodeCard);
  });
}

function setupLaunchStep() {
  const summaryDiv = document.getElementById('launch-summary');

  if (selectedProfile.node_count === 1) {
    const nodeHostname = document.getElementById('input-node').value;
    const imageSelect = document.getElementById('image-select');

    summaryDiv.innerHTML = `
      <div class="message message-info">
        <h3>Launch Configuration</h3>
        <strong>Profile:</strong> ${selectedProfile.name}<br>
        <strong>Docker Image:</strong> ${imageSelect.options[imageSelect.selectedIndex].text}<br>
        <strong>Node:</strong> ${nodeHostname}<br>
        <strong>Resources:</strong> ${selectedProfile.cpu_requirement} CPU, ${selectedProfile.memory_requirement} GB RAM
      </div>
    `;
  } else {
    summaryDiv.innerHTML = `
      <div class="message message-info">
        <h3>Multi-Node Launch Configuration</h3>
        <strong>Profile:</strong> ${selectedProfile.name}<br>
        <strong>Nodes:</strong> ${allocatedNodes.length} allocated<br>
        <strong>Total Resources:</strong> ${allocatedNodes.length * selectedProfile.cpu_requirement} CPU,
        ${allocatedNodes.length * selectedProfile.memory_requirement} GB RAM<br>
        <strong>Primary Node:</strong> ${allocatedNodes[0]?.hostname || 'Not allocated'}
      </div>
    `;
  }
}

function isNodeHealthy(node) {
  const totalActiveContainers = (node.active_jupyterlab || 0) + (node.active_ray || 0);
  const cpuUsage = node.cpu_usage_percent || 0;
  const memUsage = node.memory_usage_percent || 0;
  return totalActiveContainers < 5 && cpuUsage <= 60 && memUsage <= 60;
}

// Form submission handler
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('spawn-form').addEventListener('submit', function(e) {
    if (selectedProfile.node_count > 1) {
      // Update session config for multi-node
      const sessionConfig = {
        profile_id: selectedProfile.id,
        allocated_nodes: allocatedNodes.map(n => n.hostname),
        node_count: selectedProfile.node_count
      };

      document.getElementById('input-session-config').value = JSON.stringify(sessionConfig);
    }

    // Validate required fields
    const nodeInput = document.getElementById('input-node');
    const nodeIpInput = document.getElementById('input-node-ip');

    if (!nodeInput.value || !nodeIpInput.value) {
      e.preventDefault();
      alert('Node allocation incomplete. Please wait or try refreshing the page.');
      return false;
    }

    // Show loading state
    const submitBtn = document.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Starting Server...';

    return true;
  });

  // Update image selection for single-node configs
  const imageSelect = document.getElementById('image-select');
  if (imageSelect) {
    imageSelect.addEventListener('change', function() {
      if (selectedProfile && selectedProfile.node_count === 1) {
        const imageValue = this.value;
        const selectedOption = this.options[this.selectedIndex];
        const description = selectedOption.getAttribute('data-desc') || '';
        const isGpu = imageValue.toLowerCase().includes('gpu');

        const imageInfo = document.getElementById('image-info');
        if (imageInfo) {
          imageInfo.innerHTML = `<strong>${isGpu ? 'GPU' : 'CPU'} Image:</strong> ${description}`;
        }

        // Re-select optimal node if GPU requirement changed
        if (selectedProfile.gpu_required !== isGpu) {
          selectOptimalNode();
        }
      }
    });
  }
});