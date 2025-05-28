import os, logging, sys
from dotenv import load_dotenv
from spawner.patched import PatchedMultiNodeSpawner

sys.path.insert(0, os.path.dirname(__file__))
c = get_config()
load_dotenv()

# ------------------------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------------------------
required_env = ["CONFIGPROXY_AUTH_TOKEN", "DOCKER_NOTEBOOK_IMAGE", "JUPYTERHUB_ADMIN"]
missing = [key for key in required_env if not os.getenv(key)]
if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

# ------------------------------------------------------------------------------
# Spawner Setup
# ------------------------------------------------------------------------------
c.JupyterHub.spawner_class = PatchedMultiNodeSpawner
c.PatchedMultiNodeSpawner.use_external_server_url = True
c.Spawner.options_form = open("src/form.html").read()

c.DockerSpawner.allowed_images = {
    "danielcristh0/jupyterlab:cpu": "danielcristh0/jupyterlab:cpu",
    "danielcristh0/jupyterlab:gpu": "danielcristh0/jupyterlab:gpu",
}

def options_from_form(formdata):
    logger = logging.getLogger("jupyterhub")
    logger.info(f"[FORM DEBUG] Received formdata: {dict(formdata)}")

    raw_image = formdata.get("image", ["danielcristh0/jupyterlab:cpu"])[0].strip()
    allowed_images = c.DockerSpawner.allowed_images

    if raw_image not in allowed_images:
        raise ValueError(f"Image not allowed: {raw_image}")

    node = formdata.get("node", [""])[0]
    node_ip = formdata.get("node_ip", [""])[0]

    if not node_ip or node_ip in ['127.0.0.1', 'localhost', '0.0.0.0']:
        raise ValueError(f"Invalid node IP: {node_ip}")

    return {"image": allowed_images[raw_image], "node": node, "node_ip": node_ip}

c.Spawner.options_from_form = options_from_form

# Hooks
PatchedMultiNodeSpawner.pre_spawn_hook = staticmethod(lambda spawner: spawner.log.info(f"[HOOK] pre_spawn {spawner.user.name}"))
PatchedMultiNodeSpawner.post_start_hook = staticmethod(lambda spawner: spawner.log.info(f"[HOOK] post_start {spawner.user.name}"))

c.Spawner.start_timeout = 600
c.Spawner.http_timeout = 300
c.Spawner.poll_interval = 30
c.Spawner.name_template = "jupyterlab-{username}"
c.Spawner.debug = True

c.DockerSpawner.image = os.environ.get("DOCKER_NOTEBOOK_IMAGE", "danielcristh0/jupyterlab:cpu")
c.DockerSpawner.notebook_dir = "/home/jovyan/work"
c.DockerSpawner.port = 0
c.DockerSpawner.use_internal_ip = False
c.DockerSpawner.volumes = {
    "jupyterhub-user-{username}": "/home/jovyan/work",
    "shared-data": "/home/jovyan/shared"
}
c.DockerSpawner.cpu_limit = 2.0
c.DockerSpawner.mem_limit = '4G'

c.Spawner.default_url = '/lab'
c.Spawner.disable_user_config = True

# ------------------------------------------------------------------------------
# Hub Setup
# ------------------------------------------------------------------------------
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = "192.168.122.1"
c.JupyterHub.hub_port = 18000
c.JupyterHub.hub_bind_url = "http://0.0.0.0:18000"
c.JupyterHub.bind_url = "http://proxy:8000"
c.JupyterHub.proxy_class = 'jupyterhub.proxy.ConfigurableHTTPProxy'
c.ConfigurableHTTPProxy.should_start = False
c.ConfigurableHTTPProxy.api_url = 'http://proxy:8001'
c.ConfigurableHTTPProxy.auth_token = os.environ["CONFIGPROXY_AUTH_TOKEN"]

c.JupyterHub.db_url = "sqlite:///data/jupyterhub.sqlite"
c.JupyterHub.cookie_secret_file = '/data/jupyterhub_cookie_secret'

c.JupyterHub.redirect_to_server = False
c.JupyterHub.implicit_spawn_seconds = 1

# ------------------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------------------
c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"
c.Authenticator.allow_all = True
c.NativeAuthenticator.open_signup = True
c.NativeAuthenticator.minimum_password_length = 8
c.NativeAuthenticator.enable_signup = True
c.Authenticator.admin_users = set(os.environ.get("JUPYTERHUB_ADMIN", "").split(","))

c.JupyterHub.public_host = "http://192.168.122.1:18081"
c.JupyterHub.tornado_settings = {
    'headers': {
        'Content-Security-Policy': "frame-ancestors 'self' *"
    }
}

# ------------------------------------------------------------------------------
# Debugging
# ------------------------------------------------------------------------------
# c.JupyterHub.debug_proxy = True
# c.Application.log_level = 'DEBUG'