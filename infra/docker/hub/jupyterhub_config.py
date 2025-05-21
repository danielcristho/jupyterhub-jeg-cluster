import os, sys, requests, json, logging
from tornado.web import RequestHandler
from jinja2 import Template

sys.path.insert(0, os.path.dirname(__file__))
from MultiNodeSpawner import MultiNodeSpawner

c = get_config()

# ------------------------------------------------------------------------------
# Render form and parse selected options
# ------------------------------------------------------------------------------

def options_from_form(formdata):
    image = formdata.get("image", ["danielcristh0/jupyterlab:cpu"])[0]
    use_gpu = any(x in image for x in ["gpu", "cu", "tf", "rpl"])

    try:
        # Fetch all available nodes
        resp = requests.get("http://172.18.0.4:15002/available-nodes", timeout=3)
        nodes = resp.json()
    except Exception as e:
        raise ValueError(f"Failed to get available nodes: {e}")

    # Filter by GPU if needed
    if use_gpu:
        nodes = [n for n in nodes if n.get("has_gpu")]
        if not nodes:
            raise ValueError("No GPU nodes available for selected image.")
    else:
        nodes = [n for n in nodes if not n.get("has_gpu")]

    if not nodes:
        raise ValueError("No suitable node found.")

    # Select node with lowest memory usage
    selected = min(nodes, key=lambda n: n.get("memory_usage_percent", 100))
    node = selected.get("hostname")

    logger = logging.getLogger("jupyterhub")
    logger.info(f"[AUTO-MATCH] Image: {image} → Node: {node} (GPU: {use_gpu})")

    return {"node": node, "image": image}

c.Spawner.options_from_form = options_from_form

# ------------------------------------------------------------------------------
# HOOK: Set image, runtime, and node selection before spawn
# ------------------------------------------------------------------------------

def pre_spawn_hook(spawner):
    opts = spawner.user_options
    node = opts.get("node", "")
    image = opts.get("image", "danielcristh0/jupyterlab:cpu")

    spawner.image = image
    spawner.log.info(f"[IMAGE] Using image: {image}")

    # Log node (only informative for now in DockerSpawner)
    if node:
        spawner.log.info(f"[NODE] Requested node: {node} (ignored in DockerSpawner)")

    # GPU runtime detection based on image name
    if any(x in image for x in ["gpu", "cu", "tf", "rpl"]):
        spawner.extra_host_config = spawner.extra_host_config or {}
        spawner.extra_host_config["runtime"] = "nvidia"
        spawner.log.info("[GPU] GPU image detected; enabling GPU runtime.")
    else:
        if spawner.extra_host_config and "runtime" in spawner.extra_host_config:
            del spawner.extra_host_config["runtime"]
        spawner.log.info("[CPU] CPU image detected.")

c.Spawner.pre_spawn_hook = pre_spawn_hook

# ------------------------------------------------------------------------------
# API Endpoint for Form
# ------------------------------------------------------------------------------

class AvailableNodesHandler(RequestHandler):
    def get(self):
        try:
            resp = requests.get("http://10.21.73.122:15002/all-nodes", timeout=3)
            data = resp.json()
            data = data.get("data", data)
            available = [n for n in data if not n.get("is_in_use_by_jupyterhub")]
            self.write(json.dumps(available))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))

c.JupyterHub.extra_handlers = [(r"/hub/api/available-nodes", AvailableNodesHandler)]

# ------------------------------------------------------------------------------
# SPAWNER CONFIGURATION (DockerSpawner)
# ------------------------------------------------------------------------------

c.JupyterHub.spawner_class = MultiNodeSpawner

# Default image and Docker network from environment
c.DockerSpawner.image = os.environ.get("DOCKER_NOTEBOOK_IMAGE", "danielcristh0/jupyterlab:cpu")
network_name = os.environ.get("DOCKER_NETWORK_NAME", "jupyterhub-net")

c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = network_name
c.DockerSpawner.extra_host_config = {
    "network_mode": network_name,
    "runtime": "nvidia"
}

c.DockerSpawner.allowed_images = {
    "danielcristh0/jupyterlab:cpu": "JupyterLab CPU",
    "danielcristh0/jupyterlab:rpl": "JupyterLab GPU (PyTorch)",
    "danielcristh0/jupyterlab:cu121": "JupyterLab CUDA 12.1",
    "danielcristh0/jupyterlab:tf": "JupyterLab TensorFlow"
}

# Notebook home dir
notebook_dir = os.environ.get("DOCKER_NOTEBOOK_DIR", "/home/jovyan/work")
c.DockerSpawner.notebook_dir = notebook_dir

# Mount volumes
c.DockerSpawner.volumes = {
    "jupyterhub-user-{username}": notebook_dir,
    "shared-data": "/home/jovyan/shared"
}

# DockerSpawner housekeeping
c.DockerSpawner.remove = True
c.DockerSpawner.debug = True
c.DockerSpawner.name_template = "jupyter-{username}"

# CPU & memory control
c.DockerSpawner.cpu_limit = 2.0
c.DockerSpawner.cpu_guarantee = 1.0
c.DockerSpawner.mem_limit = '4G'
c.DockerSpawner.mem_guarantee = '2G'

# ------------------------------------------------------------------------------
# JUPYTERHUB CORE SETTINGS
# ------------------------------------------------------------------------------

c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 18000
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"
c.JupyterHub.cookie_max_age_days = 7
c.JupyterHub.shutdown_on_logout = True
c.JupyterHub.active_server_limit = 100
c.JupyterHub.last_activity_interval = 300

# ------------------------------------------------------------------------------
# AUTHENTICATION CONFIG (NativeAuthenticator)
# ------------------------------------------------------------------------------

c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"
c.Authenticator.allow_all = True
c.NativeAuthenticator.open_signup = True
c.NativeAuthenticator.minimum_password_length = 8

admins = os.environ.get("JUPYTERHUB_ADMIN", "")
c.Authenticator.admin_users = set(admins.split(",")) if admins else set()

# ------------------------------------------------------------------------------
# IDLE CULLER SERVICE
# ------------------------------------------------------------------------------

c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "admin": True,
        "command": [
            sys.executable, "-m", "jupyterhub_idle_culler",
            "--timeout=900",     # 15 mins idle
            "--cull-every=60",   # check every 1 min
            "--max-age=28800",   # 8 hours
            "--concurrency=10"
        ],
    }
]

c.JupyterHub.load_roles = [
    {
        "name": "idle-culler",
        "scopes": [
            "list:users", "read:users:activity",
            "read:servers", "delete:servers"
        ],
        "services": ["idle-culler"]
    }
]

# ------------------------------------------------------------------------------
# Monitoring
# ------------------------------------------------------------------------------

c.JupyterHub.authenticate_prometheus = False
c.ResourceUseDisplay.track_cpu_percent = True
