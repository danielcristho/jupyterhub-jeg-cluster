import os, sys, json, logging, asyncio, requests, time
from dotenv import load_dotenv
from traitlets import Bool, Unicode
import docker

sys.path.insert(0, os.path.dirname(__file__))
from MultiNodeSpawner import MultiNodeSpawner

c = get_config()

# ------------------------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------------------------
load_dotenv()
required_env = ["CONFIGPROXY_AUTH_TOKEN", "DOCKER_NOTEBOOK_IMAGE", "JUPYTERHUB_ADMIN"]
missing = [key for key in required_env if not os.getenv(key)]
if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

DISCOVERY_API_URL = os.environ.get("DISCOVERY_API_URL", "http://192.168.100.102:15002") # Discovery Service

# ------------------------------------------------------------------------------
# Custom MultiNodeSpawner with Fixed Networking
# ------------------------------------------------------------------------------
class PatchedMultiNodeSpawner(MultiNodeSpawner):
    use_external_server_url = Bool(True).tag(config=True)

    server_ip = Unicode("").tag(config=True)
    server_port = Unicode("").tag(config=True)

    async def start(self):
        self.log.info("[START] Overriding start() to get real IP:Port")

        if not hasattr(self, 'host') or 'tcp://127.0.0.1' in self.host or self.host == "tcp://127.0.0.1:2375":
            self.log.error(f"[START] CRITICAL: Spawner host is still local: {getattr(self, 'host', 'not set')}")
            raise Exception("Remote host not properly configured. Cannot spawn to local machine.")

        self.log.info(f"[START] Using remote Docker host: {self.host}")

        # Call parent start method
        container_id = await super().start()

        try:
            await asyncio.sleep(5)

            # Get container info
            container = self.client.inspect_container(self.container_id)
            ports = container["NetworkSettings"]["Ports"]

            if "8888/tcp" in ports and ports["8888/tcp"]:
                host_port = ports["8888/tcp"][0]["HostPort"]
                node_ip = self.host.replace("tcp://", "").split(":")[0]

                # Set the IP and port for the spawner
                self.ip = node_ip
                self.port = int(host_port)

                self.server_ip = node_ip
                self.server_port = str(host_port)

                self.log.info(f"[START] Container spawned successfully")
                self.log.info(f"[START] External access: {self.ip}:{self.port}")
                self.log.info(f"[START] Server URL will be: http://{self.server_ip}:{self.server_port}")
            else:
                raise Exception("Port 8888 not exposed or not found in container ports")

            if container["State"]["Status"] != "running":
                raise Exception(f"Container not running: {container['State']['Status']}")

            # Test connectivity to the spawned server
            await self._wait_for_server_ready()

        except Exception as e:
            self.log.error(f"[START] Failed to configure or verify container: {e}")
            # Clean up on failure
            try:
                self.client.remove_container(self.container_id, force=True)
            except:
                pass
            raise

        return container_id

    async def _wait_for_server_ready(self, timeout=60):
        """Wait for the Jupyter server to be ready and responding"""
        import aiohttp

        url = f"http://{self.ip}:{self.port}/user/{self.user.name}/"
        self.log.info(f"[START] Waiting for server to be ready at {url}")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.get(url, allow_redirects=False) as resp:
                        if resp.status in (200, 302):
                            self.log.info(f"[START] Server is ready at {url}")
                            return True
            except Exception as e:
                self.log.debug(f"[START] Server not ready yet: {e}")
                await asyncio.sleep(2)

        raise Exception(f"Server not ready after {timeout} seconds at {url}")

    async def poll(self):
        """Override poll to properly check container status"""
        try:
            if not hasattr(self, 'container_id') or not self.container_id:
                self.log.warning("[POLL] No container_id set")
                return 1

            for _ in range(3):
                try:
                    container = self.client.inspect_container(self.container_id)
                    break
                except docker.errors.NotFound:
                    self.log.warning(f"[POLL] Container not found yet, retrying...")
                    await asyncio.sleep(2)
            else:
                raise Exception(f"[POLL] Container {self.container_id} not found after retries.")
            state = container["State"]

            self.log.debug(f"[POLL] Container {self.container_id[:12]} state: {state['Status']}")

            if state["Status"] == "running":
                return None  # Still running
            else:
                self.log.warning(f"[POLL] Container stopped with status: {state['Status']}")
                return 1  # Stopped

        except Exception as e:
            self.log.error(f"[POLL] Failed to inspect container: {e}")
            return 1
    async def get_command(self):
        self.log.debug("[CUSTOM] get_command returning jupyterhub-singleuser")
        return ["jupyterhub-singleuser"]

    def get_args(self):
        return [
            "--ServerApp.ip=0.0.0.0",
            "--ServerApp.port=8888",
            "--ServerApp.token=",
            "--ServerApp.password=",
            "--ServerApp.allow_origin=*",
            "--ServerApp.disable_check_xsrf=True",
            "--no-browser",
            "--allow-root",
        ]

    @property
    def server_url(self):
        """Return the external URL for accessing the server"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            return f"http://{self.server_ip}:{self.server_port}"
        elif hasattr(self, 'ip') and hasattr(self, 'port') and self.ip and self.port:
            return f"http://{self.ip}:{self.port}"
        else:
            return super().server_url

# ------------------------------------------------------------------------------
# Form Setup
# ------------------------------------------------------------------------------
form_path = os.path.join(os.path.dirname(__file__), "form.html")
with open(form_path, "r") as f:
    c.Spawner.options_form = f.read()

def options_from_form(formdata):
    logger = logging.getLogger("jupyterhub")
    logger.info(f"[FORM] Received form data: {dict(formdata)}")

    raw_image = formdata.get("image", ["danielcristh0/jupyterlab:cpu"])[0]
    if isinstance(raw_image, bytes):
        raw_image = raw_image.decode("utf-8")

    allowed_images_map = {
        "danielcristh0/jupyterlab:cpu": "danielcristh0/jupyterlab:cpu",
        "danielcristh0/jupyterlab:gpu": "danielcristh0/jupyterlab:gpu",
    }
    image = allowed_images_map.get(raw_image, raw_image)
    allowed_docker_tags = list(allowed_images_map.values())

    if image not in allowed_docker_tags:
        logger.warning(f"[FORM] Image '{image}' not in allowed list, using default")
        image = "danielcristh0/jupyterlab:cpu"

    use_gpu = any(x in image for x in ["gpu", "cu", "tf", "rpl"])

    try:
        url = f"{DISCOVERY_API_URL}/available-nodes"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        nodes = resp.json()
    except Exception as e:
        raise ValueError(f"Discovery API failed: {e}")

    suitable_nodes = [n for n in nodes if n.get("has_gpu") == use_gpu or not use_gpu]
    if not suitable_nodes:
        raise ValueError("No suitable node found for the selected image.")

    selected = min(suitable_nodes, key=lambda n: n.get("memory_usage_percent", 100))
    return {
        "node": selected.get("hostname"),
        "image": image,
        "node_ip": selected.get("ip")
    }

c.Spawner.options_from_form = options_from_form

# ------------------------------------------------------------------------------
# Pre/Post Spawn Hooks
# ------------------------------------------------------------------------------
def pre_spawn_hook(spawner):
    """Configure spawner before container creation"""
    opts = spawner.user_options
    node = opts.get("node", "")
    node_ip = opts.get("node_ip", "")
    image = opts.get("image", "danielcristh0/jupyterlab:cpu")

    if not node or not node_ip:
        raise ValueError("Remote node configuration is missing. Cannot spawn locally.")

    spawner.log.info(f"[PRE_SPAWN] Configuring for node {node} ({node_ip})")

    # Basic spawner configuration
    spawner.image = image
    spawner.host = f"tcp://{node_ip}:2375"
    spawner.tls_config = {}
    spawner.port = 8888
    spawner.use_internal_ip = False

    # Environment variables for Jupyter
    spawner.environment = {
        'JUPYTER_ENABLE_LAB': 'yes',
        'RESTARTABLE': 'yes',
        'JUPYTER_TOKEN': '',
        'JUPYTER_ALLOW_INSECURE_WRITES': 'true',
        'JUPYTER_PORT': '8888',
        'JUPYTER_IP': '0.0.0.0',
        'JUPYTERHUB_SERVICE_URL': 'http://192.168.100.246:18000/hub/'
    }

    # Container runtime configuration
    runtime = {"runtime": "nvidia"} if any(x in image for x in ["gpu", "cu", "tf", "rpl"]) else {}

    spawner.extra_host_config = {
        **runtime,
        "port_bindings": {
            8888: ('0.0.0.0',),  # Bind to all interfaces on host
            "8888/tcp": ("0.0.0.0", None)
        },
        "extra_hosts": {
            "jupyterhub": "192.168.100.246",  # External hub IP for spawned containers
            "hub": "192.168.100.246"  # Additional alias
        }
    }

    spawner.log.info(f"[PRE_SPAWN] Configuration complete for {node_ip}")

async def post_start_hook(spawner):
    """Configure spawner after container is running"""
    try:
        await asyncio.sleep(3)  # Give container time to start

        container = spawner.client.inspect_container(spawner.container_id)
        ports = container["NetworkSettings"]["Ports"]

        if "8888/tcp" not in ports or not ports["8888/tcp"]:
            raise Exception("Port 8888 not properly exposed")

        host_port = ports["8888/tcp"][0]["HostPort"]
        node_ip = spawner.host.replace("tcp://", "").split(":")[0]

        # Set all necessary attributes for external access
        spawner.ip = node_ip
        spawner.port = int(host_port)
        spawner.server_ip = node_ip
        spawner.server_port = int(host_port)

        spawner.log.info(f"[POST_START] Server configured at {node_ip}:{host_port}")
        spawner.log.info(f"[POST_START] External URL: http://{node_ip}:{host_port}")

    except Exception as e:
        spawner.log.error(f"[POST_START] Hook failed: {e}")
        raise

# Attach hooks to spawner class
PatchedMultiNodeSpawner.pre_spawn_hook = staticmethod(pre_spawn_hook)
PatchedMultiNodeSpawner.post_start_hook = staticmethod(post_start_hook)

# ------------------------------------------------------------------------------
# Core JupyterHub Configuration
# ------------------------------------------------------------------------------
c.JupyterHub.spawner_class = PatchedMultiNodeSpawner

c.JupyterHub.hub_ip = "0.0.0.0"  # Bind to all interfaces inside container
c.JupyterHub.hub_connect_ip = "192.168.100.246"  # External IP for spawners to connect back
c.JupyterHub.hub_port = 18000  # Hub API port
c.JupyterHub.bind_url = "http://proxy:8000"  # Proxy handles public access
c.JupyterHub.hub_bind_url = "http://0.0.0.0:18000"  # Hub binds internally

# Database and secrets
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

# Performance settings
c.JupyterHub.shutdown_on_logout = True
c.JupyterHub.active_server_limit = 100
c.JupyterHub.last_activity_interval = 300
c.JupyterHub.log_level = 'DEBUG'

c.JupyterHub.proxy_class = 'jupyterhub.proxy.ConfigurableHTTPProxy'
c.ConfigurableHTTPProxy.should_start = False  # External proxy container
c.ConfigurableHTTPProxy.api_url = 'http://proxy:8001'  # Internal network communication
c.ConfigurableHTTPProxy.public_url = 'http://192.168.100.246:18081'  # External access URL
c.ConfigurableHTTPProxy.auth_token = os.environ.get("CONFIGPROXY_AUTH_TOKEN")

# ------------------------------------------------------------------------------
# Spawner Timeout Configuration
# ------------------------------------------------------------------------------
c.Spawner.start_timeout = 300  # 5 minutes to start
c.Spawner.http_timeout = 180   # 3 minutes to respond
c.DockerSpawner.start_timeout = 300
c.DockerSpawner.http_timeout = 180

# Additional timeout settings
c.Spawner.poll_interval = 30  # Check container status every 30s

# ------------------------------------------------------------------------------
# DockerSpawner Defaults & Images
# ------------------------------------------------------------------------------
c.DockerSpawner.image = os.environ.get("DOCKER_NOTEBOOK_IMAGE", "danielcristh0/jupyterlab:cpu")
c.DockerSpawner.use_internal_ip = False
c.DockerSpawner.notebook_dir = "/home/jovyan/work"
# c.DockerSpawner.remove = True
c.DockerSpawner.debug = True
c.DockerSpawner.name_template = "jupyterlab-{username}"

# Volume configuration
c.DockerSpawner.volumes = {
    "jupyterhub-user-{username}": c.DockerSpawner.notebook_dir,
    "shared-data": "/home/jovyan/shared"
}

# Resource limits
c.DockerSpawner.cpu_limit = 2.0
c.DockerSpawner.cpu_guarantee = 1.0
c.DockerSpawner.mem_limit = '4G'
c.DockerSpawner.mem_guarantee = '2G'

# Default container configuration
c.DockerSpawner.extra_host_config = {
    "extra_hosts": {
        "jupyterhub": "192.168.100.246",
        "hub": "192.168.100.246"
    },
    "port_bindings": {
        8888: ('0.0.0.0',),
        "8888/tcp": ("0.0.0.0", None)
    }
}

c.DockerSpawner.allowed_images = {
    "danielcristh0/jupyterlab:cpu": "danielcristh0/jupyterlab:cpu",
    "danielcristh0/jupyterlab:gpu": "danielcristh0/jupyterlab:gpu"
}

# ------------------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------------------
c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"
c.Authenticator.allow_all = True
c.NativeAuthenticator.open_signup = True
c.NativeAuthenticator.minimum_password_length = 8

# Admin users
admins = os.environ.get("JUPYTERHUB_ADMIN", "")
c.Authenticator.admin_users = set(admins.split(",")) if admins else set()
c.NativeAuthenticator.enable_signup = True
c.NativeAuthenticator.create_system_users = False

# ------------------------------------------------------------------------------
# Monitoring & Debugging
# ------------------------------------------------------------------------------
c.JupyterHub.authenticate_prometheus = False
c.ResourceUseDisplay.track_cpu_percent = True

# Enable additional debugging
c.Application.log_level = 'DEBUG'
c.JupyterHub.debug_proxy = True