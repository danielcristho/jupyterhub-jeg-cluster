const API_URL = "http://10.33.17.30:15002";

const { createApp, ref, reactive, computed, onMounted } = Vue;

createApp({
    setup() {
        const status = reactive({
            type: 'info',
            message: 'Connecting to service...'
        });
        const profiles = ref([]);
        const nodes = ref([]);
        const selectedProfile = ref(null);
        const selectedNodes = ref([]);
        const numNodes = ref(1);
        const nodeConfig = ref('single');
        const selectedImage = ref('danielcristh0/jupyterlab:cpu');
        const isLoading = ref(true);
        const nodeError = ref('');

        const isMultiNode = computed(() => selectedProfile.value && selectedProfile.value.max_nodes > 1);
        const isMultiConfig = computed(() => nodeConfig.value === 'multi');

        // =================================
        // Interaksi dengan Discovery API
        // =================================
        async function checkAPI() {
            try {
                const resp = await fetch(`${API_URL}/health-check`);
                if (resp.ok) {
                    status.type = 'success';
                    status.message = 'Discovery Service Connected';
                } else {
                    throw new Error('API not responding');
                }
            } catch (e) {
                status.type = 'warning';
                status.message = 'Offline Mode - Using default configuration';
                profiles.value = getFallbackProfiles();
                nodes.value = [];
            }
        }

        async function loadProfiles() {
            try {
                const resp = await fetch(`${API_URL}/profiles`);
                if (resp.ok) {
                    const data = await resp.json();
                    profiles.value = data.profiles || getFallbackProfiles();
                } else {
                    throw new Error('Failed to load profiles');
                }
            } catch (e) {
                console.error('Error loading profiles:', e);
                profiles.value = getFallbackProfiles();
            }
        }

        async function loadNodes() {
            try {
                const resp = await fetch(`${API_URL}/available-nodes`);
                if (resp.ok) {
                    const data = await resp.json();
                    nodes.value = data.all_available_nodes || [];
                }
            } catch (e) {
                console.log('Could not fetch available nodes:', e);
                nodes.value = [];
            }
        }

        // =================================
        // Core logic & State Management
        // =================================
        async function selectProfile(profile) {
            selectedProfile.value = profile;
            nodeConfig.value = profile.max_nodes > 1 ? nodeConfig.value : 'single';
            selectedImage.value = profile.gpu_required ? 'danielcristh0/jupyterlab:gpu' : 'danielcristh0/jupyterlab:cpu';
            
            await displayNodes();
        }

        async function displayNodes() {
            if (!selectedProfile.value) return;

            nodeError.value = '';
            isLoading.value = true;
            
            const nodesToSelect = isMultiConfig.value ? parseInt(numNodes.value) : 1;

            try {
                const resp = await fetch(`${API_URL}/select-nodes`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        profile_id: selectedProfile.value.id,
                        num_nodes: nodesToSelect,
                        user_id: 'jupyterhub-user'
                    })
                });

                if (!resp.ok) {
                    const errorData = await resp.json().catch(() => ({ error: 'Failed to select nodes' }));
                    throw new Error(errorData.error);
                }
                
                const data = await resp.json();
                selectedNodes.value = data.selected_nodes || [];
            } catch (e) {
                console.error('Error selecting nodes:', e);
                nodeError.value = `Error selecting nodes: ${e.message}`;
                selectedNodes.value = [];
            } finally {
                isLoading.value = false;
            }
        }
        
        const totalCPU = computed(() => selectedNodes.value.reduce((sum, n) => sum + (n.cpu_cores || 0), 0));
        const totalRAM = computed(() => selectedNodes.value.reduce((sum, n) => sum + (n.ram_gb || 0), 0));
        const hasGPU = computed(() => selectedNodes.value.some(n => n.has_gpu));

        function getFallbackProfiles() {
            return [
                { id: 1, name: 'single-cpu', description: 'Single node with CPU only', min_nodes: 1, max_nodes: 1, cpu_requirement: 2, ram_requirement: 2, gpu_required: false },
                { id: 2, name: 'single-gpu', description: 'Single node with GPU acceleration', min_nodes: 1, max_nodes: 1, cpu_requirement: 2, ram_requirement: 2, gpu_required: true },
                { id: 3, name: 'multi-cpu', description: 'Multiple nodes with CPU only', min_nodes: 2, max_nodes: 4, cpu_requirement: 2, ram_requirement: 2, gpu_required: false },
                { id: 4, name: 'multi-gpu', description: 'Multiple nodes with GPU acceleration', min_nodes: 2, max_nodes: 4, cpu_requirement: 2, ram_requirement: 2, gpu_required: true }
            ];
        }

        function getDisplayName(profileName) {
            const words = profileName.split('-');
            return words.map(word => {
                if (word.toUpperCase() === 'CPU' || word.toUpperCase() === 'GPU') {
                    return word.toUpperCase();
                }
                return word.charAt(0).toUpperCase() + word.slice(1);
            }).join(' ');
        }

        function getNodeStatus(node) {
            const cpu = node.cpu_usage_percent || 0;
            const mem = node.memory_usage_percent || 0;
            let status = 'healthy';
            let statusText = 'Available';
            if (cpu > 80 || mem > 80) { status = 'overloaded'; statusText = 'High Load'; } 
            else if (cpu > 60 || mem > 60) { status = 'busy'; statusText = 'Moderate Load'; }
            return { status, statusText, cpu, mem };
        }
        
        function handleNext() {
            if (!selectedProfile.value || selectedNodes.value.length === 0) {
                alert("Please select a profile and wait for node selection before proceeding.");
                return;
            }

            const finalConfig = {
                profile_id: selectedProfile.value.id,
                profile_name: selectedProfile.value.name,
                image: selectedImage.value,
                node_count: selectedNodes.value.length,
                primary_node: selectedNodes.value.length > 0 ? selectedNodes.value[0].hostname : '',
                selected_nodes: selectedNodes.value
            };
            
            console.log('[NEXT_BUTTON] Saving config to localStorage:', finalConfig);
            localStorage.setItem("jupyterhub_spawn_config", JSON.stringify(finalConfig));
        }

        // Lifecycle hook
        onMounted(async () => {
            await checkAPI();
            await Promise.all([loadProfiles(), loadNodes()]);
            if (profiles.value.length > 0) {
                selectProfile(profiles.value[0]);
            }
            // Refresh nodes every 30 seconds
            setInterval(async () => {
                if (selectedProfile.value) {
                    await loadNodes();
                    await displayNodes();
                }
            }, 30000);
        });

        // Expose ke template
        return {
            status,
            profiles,
            nodes,
            selectedProfile,
            selectedNodes,
            nodeConfig,
            numNodes,
            selectedImage,
            isLoading,
            nodeError,
            isMultiNode,
            isMultiConfig,
            selectProfile,
            displayNodes,
            totalCPU,
            totalRAM,
            hasGPU,
            getDisplayName,
            getNodeStatus,
            handleNext
        };
    }
}).mount('#app');