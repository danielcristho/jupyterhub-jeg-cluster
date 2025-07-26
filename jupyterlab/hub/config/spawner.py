import os
import json
from spawner.multinode import MultiNodeSpawner
from tornado.web import StaticFileHandler

STATIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "form"))

def options_from_form(formdata):
    import logging
    logger = logging.getLogger("jupyterhub")

    raw = formdata.get('selected_nodes', ['[]'])[0]
    logger.info(f"[DEBUG] raw selected_nodes: {raw} ({type(raw)})")

    selected_nodes = []
    
    if isinstance(raw, str):
        if raw.strip():
            try:
                selected_nodes = json.loads(raw)
                logger.info(f"[DEBUG] Successfully parsed JSON: {len(selected_nodes)} nodes")
            except json.JSONDecodeError as e:
                logger.warning(f"[options_from_form] Failed to parse JSON '{raw}': {e}")
                selected_nodes = []
        else:
            logger.warning(f"[options_from_form] Empty string received")
            selected_nodes = []
    elif isinstance(raw, list):
        selected_nodes = raw
        logger.info(f"[DEBUG] Using list directly: {len(selected_nodes)} nodes")
    else:
        logger.error(f"[options_from_form] Unexpected type: {type(raw)}")
        selected_nodes = []

    # Additional validation
    if not isinstance(selected_nodes, list):
        logger.error(f"[DEBUG] selected_nodes is not a list: {type(selected_nodes)}")
        selected_nodes = []

    # Validate each node has required fields
    validated_nodes = []
    for i, node in enumerate(selected_nodes):
        if isinstance(node, dict) and 'ip' in node and 'hostname' in node:
            validated_nodes.append(node)
            logger.info(f"[DEBUG] Node {i} valid: {node.get('hostname')} ({node.get('ip')})")
        else:
            logger.warning(f"[DEBUG] Node {i} invalid or missing keys: {node}")

    logger.info(f"[FORM_DATA] Final validated nodes: {len(validated_nodes)}")

    return {
        'profile_id': formdata.get('profile_id', [''])[0],
        'profile_name': formdata.get('profile_name', [''])[0],
        'selected_nodes': validated_nodes,
        'primary_node': formdata.get('primary_node', [''])[0],
        'image': formdata.get('image', [''])[0],
    }

def configure_spawner(c):
    c.JupyterHub.spawner_class = MultiNodeSpawner
    c.Spawner.options_from_form = options_from_form 

    c.MultiNodeSpawner.discovery_api_url = os.environ.get(
        'DISCOVERY_API_URL',
        'http://10.33.17.30:15002'
    )
    c.MultiNodeSpawner.enable_multi_node = True

    form_path = os.path.join(STATIC_PATH, "form.html")
    if os.path.exists(form_path):
        with open(form_path, 'r', encoding='utf-8') as f:
            c.Spawner.options_form = f.read()

        c.JupyterHub.extra_handlers = [
            (r"/form/(.*)", StaticFileHandler, {"path": STATIC_PATH})
        ]
    else:
        c.Spawner.options_form = """<div>Simple fallback form loaded.</div>"""
    
    allowed_images = {
        "danielcristh0/jupyterlab:cpu": "danielcristh0/jupyterlab:cpu",
        "danielcristh0/jupyterlab:gpu": "danielcristh0/jupyterlab:gpu",
    }
    c.DockerSpawner.allowed_images = allowed_images

    c.Spawner.start_timeout = 600
    c.Spawner.http_timeout = 300
    c.Spawner.poll_interval = 30
    c.Spawner.name_template = "jupyterlab-{username}"
    c.Spawner.default_url = "/lab"

    c.DockerSpawner.image = "danielcristh0/jupyterlab:cpu"
    c.DockerSpawner.notebook_dir = "/home/jovyan/work"
    
    # c.DockerSpawner.volumes = {
    #     '/srv/jupyterhub/userdata/{username}': '/home/jovyan/work',
    # }

    c.DockerSpawner.volumes = {
        "jupyterhub-user-{username}": "/home/jovyan/work"
    }
    c.DockerSpawner.cpu_limit = 4.0
    c.DockerSpawner.mem_limit = "8G"
    c.DockerSpawner.remove = True
    c.DockerSpawner.debug = True
    c.DockerSpawner.use_internal_ip = False
    c.DockerSpawner.network_name = 'jupyterhub-network'
    

    # c.JupyterHub.hub_ip = '192.168.122.1'
    # c.JupyterHub.hub_port = 8081
    # c.JupyterHub.port = 8000
    # c.JupyterHub.log_level = 'DEBUG'

    c.Authenticator.admin_users = {'admin'}

    async def pre_spawn_hook(spawner):
        user_options = spawner.user_options
        profile_name = user_options.get('profile_name', 'single-cpu')

        config = {
            'single-cpu': {'cpu': 1, 'memory': '2G', 'env': {'RAY_ENABLED': 'false'}},
            'single-gpu': {'cpu': 1, 'memory': '2G', 'gpu': True, 'env': {'RAY_ENABLED': 'false'}},
            'multi-cpu': {'cpu': 1, 'memory': '2G', 'env': {'RAY_ENABLED': 'true'}},
            'multi-gpu': {'cpu': 1, 'memory': '2G', 'gpu': True, 'env': {'RAY_ENABLED': 'true'}}
        }.get(profile_name, {'cpu': 1, 'memory': '2G', 'env': {}})

        spawner.cpu_limit = config['cpu']
        spawner.mem_limit = config['memory']
        spawner.environment = spawner.environment or {}
        spawner.environment.update(config['env'])

        if config.get('gpu') and 'gpu' in user_options.get('image', '').lower():
            spawner.extra_host_config = spawner.extra_host_config or {}
            spawner.extra_host_config.update({
                'runtime': 'nvidia',
                'device_requests': [{
                    'driver': 'nvidia',
                    'capabilities': [['gpu']],
                    'count': 1
                }]
            })

        spawner.log.info(f"Spawner configured: CPU={spawner.cpu_limit}, Memory={spawner.mem_limit}, Profile={profile_name}")

    async def post_stop_hook(spawner):
        spawner.log.info(f"Post-stop cleanup for {spawner.user.name}")
        if hasattr(spawner, 'worker_containers'):
            spawner.worker_containers.clear()

    c.Spawner.pre_spawn_hook = pre_spawn_hook
    c.Spawner.post_stop_hook = post_stop_hook

    return c