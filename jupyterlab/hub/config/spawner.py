"""Spawner configuration: Integrates service discovery, multi-node spawning, and dynamic node selection"""

import os
import json
from spawner.multinode import MultiNodeSpawner
from tornado.web import StaticFileHandler

STATIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "form"))


def configure_spawner(c):
    """Configure JupyterHub to use MultiNodeSpawner with Service Discovery"""

    # Use MultiNodeSpawner
    c.JupyterHub.spawner_class = MultiNodeSpawner

    # Service Discovery Configuration
    c.MultiNodeSpawner.discovery_api_url = os.environ.get(
        'DISCOVERY_API_URL',
        'http://localhost:15002'
    )

    # Load HTML Form (yang sudah kita buat tadi)
    form_path = os.path.join(STATIC_PATH, "form.html")
    with open(form_path) as f:
        c.Spawner.options_form = f.read()

    # Serve static files (CSS, JS if needed)
    c.JupyterHub.extra_handlers = [
        (r"/form/(.*)", StaticFileHandler, {"path": STATIC_PATH})
    ]

    # Allowed Docker images
    allowed_images = {
        "danielcristh0/jupyterlab:cpu": "CPU Environment",
        "danielcristh0/jupyterlab:gpu": "GPU Environment (CUDA)",
    }
    c.DockerSpawner.allowed_images = allowed_images

    # Multi-node configuration
    c.MultiNodeSpawner.enable_multi_node = True

    # Spawner timeouts
    c.Spawner.start_timeout = 600
    c.Spawner.http_timeout = 300
    c.Spawner.poll_interval = 30

    # Container naming
    c.Spawner.name_template = "jupyterlab-{username}"
    c.Spawner.default_url = "/lab"

    # DockerSpawner base configuration
    c.DockerSpawner.image = os.environ.get(
        "DOCKER_NOTEBOOK_IMAGE",
        "danielcristh0/jupyterlab:cpu"
    )
    c.DockerSpawner.notebook_dir = "/home/jovyan/work"
    c.DockerSpawner.volumes = {
        "jupyterhub-user-{username}": "/home/jovyan/work",
        "shared-data": {
            "bind": "/home/jovyan/shared",
            "mode": "ro"  # Read-only shared data
        }
    }

    # Resource limits (akan di-override berdasarkan profile)
    c.DockerSpawner.cpu_limit = 2.0
    c.DockerSpawner.mem_limit = "4G"
    c.DockerSpawner.remove = True
    c.DockerSpawner.debug = True

    # Network configuration for multi-node
    c.DockerSpawner.network_name = "jupyterhub-network"
    c.DockerSpawner.use_internal_ip = False

    # Extra host configuration for GPU
    c.DockerSpawner.extra_host_config = {}

    # Pre-spawn hook untuk dynamic resource allocation
    async def pre_spawn_hook(spawner):
        """Dynamically set resources based on selected profile"""
        user_options = spawner.user_options
        profile_name = user_options.get('profile_name', 'basic')

        # Set resource limits based on profile
        resource_limits = {
            'basic': {'cpu': 2, 'memory': '4G'},
            'standard': {'cpu': 4, 'memory': '8G'},
            'high-performance': {'cpu': 8, 'memory': '16G'},
            'gpu-compute': {'cpu': 4, 'memory': '16G', 'gpu': True}
        }

        limits = resource_limits.get(profile_name, resource_limits['basic'])
        spawner.cpu_limit = limits['cpu']
        spawner.mem_limit = limits['memory']

        # Configure GPU if needed
        if limits.get('gpu') and user_options.get('image', '').endswith(':gpu'):
            spawner.extra_host_config = {
                'runtime': 'nvidia',
                'device_requests': [{
                    'driver': 'nvidia',
                    'capabilities': [['gpu']],
                    'count': 1  # or 'all' for all GPUs
                }]
            }

        # Log spawn information
        spawner.log.info(
            f"Pre-spawn: User {spawner.user.name} "
            f"Profile: {profile_name} "
            f"Nodes: {user_options.get('node_count', 1)} "
            f"CPU: {spawner.cpu_limit} "
            f"Memory: {spawner.mem_limit}"
        )

    c.Spawner.pre_spawn_hook = pre_spawn_hook

    # Post-stop hook untuk cleanup
    async def post_stop_hook(spawner):
        """Clean up after container stops"""
        spawner.log.info(f"Post-stop cleanup for {spawner.user.name}")
        # Additional cleanup if needed

    c.Spawner.post_stop_hook = post_stop_hook