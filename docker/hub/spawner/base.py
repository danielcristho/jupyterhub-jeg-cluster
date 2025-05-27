import os, asyncio, logging
from dockerspawner import DockerSpawner
from traitlets import Unicode, Dict
import docker

class MultiNodeSpawner(DockerSpawner):
    host = Unicode("tcp://0.0.0.0:2375", config=True)
    tls_config = Dict({}, config=True)

    node = Unicode("", config=True)
    image = Unicode("", config=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_internal_ip = False

    @property
    def ip(self):
        """Force return remote server IP"""
        if hasattr(self, 'server_ip') and self.server_ip:
            self.log.info(f"[IP_OVERRIDE] Using: {self.server_ip}")
            return self.server_ip
        return getattr(self, '_ip', '127.0.0.1')

    @ip.setter
    def ip(self, value):
        """Set IP value"""
        self._ip = value

    @property
    def port(self):
        """Force return remote server port"""
        if hasattr(self, 'server_port') and self.server_port:
            port_int = int(self.server_port)
            self.log.info(f"[PORT_OVERRIDE] Using: {port_int}")
            return port_int
        return getattr(self, '_port', 8888)

    @port.setter
    def port(self, value):
        """Set port value"""
        self._port = int(value)

    @property
    def client(self):
        """Override client property to ensure we use the updated Docker client"""
        if not hasattr(self, '_client') or self._client is None:
            self._client = self._get_client()
        elif hasattr(self, '_client') and self._client.base_url != self.host:
            try:
                self._client.close()
            except:
                pass
            self._client = self._get_client()
        return self._client

    def _get_client(self):
        """Get or create Docker client"""
        try:
            client = docker.APIClient(base_url=self.host, tls=self.tls_config)
            client.ping()
            self.log.info(f"[DOCKER_CLIENT] Connected to remote Docker: {self.host}")
            return client
        except Exception as e:
            self.log.error(f"[DOCKER_CLIENT] Failed to connect to {self.host}: {e}")
            raise

    @property
    def url(self):
        """Override URL to ensure it points to remote server"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            base_url = f"http://{self.server_ip}:{self.server_port}"
            self.log.info(f"[URL_OVERRIDE] Using URL: {base_url}")
            return base_url
        return super().url

    @property
    def server_url(self):
        """Override server_url to ensure consistency"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            url = f"http://{self.server_ip}:{self.server_port}"
            self.log.info(f"[SERVER_URL_OVERRIDE] Using server_url: {url}")
            return url
        return super().server_url

    def _get_ip_and_port(self):
        """Override internal method that DockerSpawner might use"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            result = (self.server_ip, int(self.server_port))
            self.log.info(f"[_GET_IP_PORT_OVERRIDE] Using: {result}")
            return result
        result = super()._get_ip_and_port() if hasattr(super(), '_get_ip_and_port') else (self.ip, self.port)
        self.log.info(f"[_GET_IP_PORT_DEFAULT] Using: {result}")
        return result

    async def get_ip_and_port(self):
        """Override async version if it exists"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            result = (self.server_ip, int(self.server_port))
            self.log.info(f"[ASYNC_GET_IP_PORT_OVERRIDE] Using: {result}")
            return result
        if hasattr(super(), 'get_ip_and_port') and asyncio.iscoroutinefunction(super().get_ip_and_port):
            result = await super().get_ip_and_port()
        else:
            result = (self.ip, self.port)
        self.log.info(f"[ASYNC_GET_IP_PORT_DEFAULT] Using: {result}")
        return result

    def _set_docker_client(self, client=None):
        """Set Docker client - kept for compatibility but use _get_client instead"""
        if client:
            self._client = client
        else:
            self._client = self._get_client()
        return self._client

    def get_ip_and_port(self):
        """Override to return remote server IP and port"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            result = (self.server_ip, int(self.server_port))
            self.log.info(f"[GET_IP_PORT_OVERRIDE] Using: {result}")
            return result
        result = super().get_ip_and_port()
        self.log.info(f"[GET_IP_PORT_DEFAULT] Using: {result}")
        return result

    def get_ip_and_port(self):
        """Override to return remote server IP and port (sync version)"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            result = (self.server_ip, int(self.server_port))
            self.log.info(f"[SYNC_GET_IP_PORT_OVERRIDE] Using: {result}")
            return result
        result = super().get_ip_and_port()
        self.log.info(f"[SYNC_GET_IP_PORT_DEFAULT] Using: {result}")
        return result

    def start_object(self):
        """Override the actual container start to force port binding"""
        container_info = self.client.inspect_container(self.container_id)
        self.log.info(f"[START_OBJECT] Container info: {container_info}")

        current_ports = container_info.get('HostConfig', {}).get('PortBindings', {})
        self.log.info(f"[START_OBJECT] Current port bindings: {current_ports}")

        result = super().start_object() if hasattr(super(), 'start_object') else None

        return result

    def create_object(self):
        """Override container creation to force correct port binding"""

        if not hasattr(self, 'extra_host_config'):
            self.extra_host_config = {}

        self.extra_host_config['port_bindings'] = {8888: None}

        self.extra_host_config['publish_all_ports'] = True

        self.extra_host_config.pop('network_mode', None)

        self.log.info(f"[CREATE_OBJECT] Final extra_host_config: {self.extra_host_config}")

        if hasattr(self, 'get_args'):
            args = self.get_args()
            self.log.info(f"[CREATE_OBJECT] DockerSpawner args: {args}")

        # Call parent method
        return super().create_object()

    async def start(self):
        logger = logging.getLogger("jupyterhub")
        logger.info(f"[SPAWNER] user_options: {self.user_options}")

        node_ip = self.user_options.get("node_ip")
        image = self.user_options.get("image", "danielcristh0/jupyterlab:cpu")

        if not node_ip or node_ip in ['127.0.0.1', 'localhost', '0.0.0.0']:
            raise ValueError(f"Invalid or missing remote node IP: {node_ip}")

        # Update connection settings before accessing client
        self.host = f"tcp://{node_ip}:2375"
        self.tls_config = {}
        self.use_internal_ip = False
        self.image = image

        # Reset client to force recreation with new host
        self._client = None

        # get the new client
        client = self.client
        self.log.info(f"[DEBUG] Docker client: {client.base_url}")
        self.log.info(f"[DEBUG] Docker host to be used: {self.host}")
        self.log.info(f"[DEBUG] CONNECTED TO: {client.base_url}")

        hub_ip = "192.168.122.1"

        self.environment.update({
            'JUPYTERHUB_API_URL': f'http://{hub_ip}:18000/hub/api',
        })

        self.args = [
            '--ip=0.0.0.0',
            '--port=8888',
            '--ServerApp.ip=0.0.0.0',
            '--ServerApp.port=8888',
            '--ServerApp.allow_origin=*',
            '--ServerApp.disable_check_xsrf=True'
        ]

        # self.cmd = []
        self.log.info(f"[DEBUG] Current extra_host_config: {self.extra_host_config}")

        if any(x in image for x in ["gpu", "cu", "tf", "rpl"]):
            self.extra_host_config["runtime"] = "nvidia"
        else:
            self.extra_host_config.pop("runtime", None)

        self.extra_host_config.pop("port_bindings", None)
        self.extra_host_config.pop("publish_all_ports", None)

        self.extra_host_config.pop("port_bindings", None)
        self.extra_host_config.pop("publish_all_ports", None)

        self.extra_host_config.update({
            "network_mode": "host",
            "extra_hosts": {
                "hub": "192.168.122.1",
                "jupyterhub": "192.168.122.1"
            }
        })

        self.log.info(f"[DEBUG] Updated extra_host_config: {self.extra_host_config}")

        # self.extra_create_kwargs = {}

        self.log.info(f"[DEBUG] About to start container with image: {self.image}")
        self.log.info(f"[DEBUG] extra_host_config before start: {self.extra_host_config}")
        self.log.info(f"[DEBUG] Host: {self.host}")

        # Log ALL spawner config for debugging
        self.log.info(f"[DEBUG] self.port: {getattr(self, 'port', 'NOT_SET')}")
        self.log.info(f"[DEBUG] self.use_internal_ip: {getattr(self, 'use_internal_ip', 'NOT_SET')}")
        self.log.info(f"[DEBUG] self.host_ip: {getattr(self, 'host_ip', 'NOT_SET')}")
        self.log.info(f"[DEBUG] DockerSpawner network_name: {getattr(self, 'network_name', 'NOT_SET')}")

        container_id = await super().start()
        self.log.info(f"[DEBUG] Container spawned on: {self.host}")
        self.log.info(f"[DEBUG] Container ID: {container_id}")

        # wait container full start
        await asyncio.sleep(15)

        container = self.client.inspect_container(self.container_id)
        container_state = container.get("State", {})
        self.log.info(f"[DEBUG] Container state: {container_state}")

        if not container_state.get("Running", False):
            try:
                logs = self.client.logs(self.container_id, tail=100, stdout=True, stderr=True).decode('utf-8')
                self.log.error(f"[ERROR] Container not running. Full logs:\n{logs}")
            except Exception as e:
                self.log.error(f"[ERROR] Could not get container logs: {e}")

            raise Exception(f"Container failed to start. Status: {container_state}")

        ports = container["NetworkSettings"]["Ports"]
        self.log.info(f"[DEBUG] Container ports: {ports}")

        if "8888/tcp" not in ports or not ports["8888/tcp"]:
            # Try to get container logs for debugging
            logs = self.client.logs(self.container_id, tail=50).decode('utf-8')
            self.log.error(f"[ERROR] Port 8888 not exposed. Container logs:\n{logs}")
            raise Exception("Port 8888 not exposed or not found")

        host_port = ports["8888/tcp"][0]["HostPort"]
        self.ip = node_ip
        self.port = int(host_port)
        self.server_ip = node_ip
        self.server_port = str(host_port)
        self.log.info(f"[REMOTE-CONTAINER] Jupyter running at http://{self.ip}:{self.port}")
        self.log.info(f"[REMOTE-CONTAINER] server_url = {self.server_url}")
        self.log.info(f"[SETUP] self.ip = {self.ip}")
        self.log.info(f"[SETUP] self.port = {self.port}")
        self.log.info(f"[SETUP] self.server_ip = {self.server_ip}")
        self.log.info(f"[SETUP] self.server_port = {self.server_port}")
        self.log.info(f"[SETUP] server_url = {self.server_url}")

        return container_id

    async def poll(self):
        try:
            return await super().poll()
        except Exception as e:
            self.log.error(f"[SPAWNER] Poll failed: {e}")
            return 1

    async def stop(self, now=False):
        try:
            return await super().stop(now)
        except Exception as e:
            self.log.error(f"[SPAWNER] Stop failed: {e}")

    def __del__(self):
        """Clean up Docker client on deletion"""
        if hasattr(self, '_client'):
            try:
                self._client.close()
            except:
                pass