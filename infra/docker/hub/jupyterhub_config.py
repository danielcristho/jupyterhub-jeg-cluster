import os, sys, requests, json, logging
from tornado.web import RequestHandler
from jinja2 import Template

sys.path.insert(0, os.path.dirname(__file__))
from MultiNodeSpawner import MultiNodeSpawner

c = get_config()

# ------------------------------------------------------------------------------
# Render form and parse selected options
# ------------------------------------------------------------------------------

def options_form(spawner):
    with open("/etc/jupyterhub/form.html") as f:
        return Template(f.read()).render()

c.Spawner.options_form = options_form

def options_from_form(formdata):
    node = formdata.get("node", [""])[0]
    image = formdata.get("image", ["danielcristh0/jupyterlab:cpu"])[0]

    if not node:
        raise ValueError("Node selection is required.")
    if not image:
        raise ValueError("Image selection is required.")

    logger = logging.getLogger("jupyterhub")
    logger.info(f"[FORM OPTIONS] Node: {node}, Image: {image}")

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
            resp = requests.get("http://127.0.0.1:15002/all-nodes", timeout=3)
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
