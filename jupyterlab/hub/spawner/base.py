"""
Enhanced Multi-Node Spawner with Service Discovery Integration
Based on your existing MultiNodeSpawner with multi-node support
"""

import os
import asyncio
import logging
import docker
import json
import requests
from dockerspawner import DockerSpawner
from traitlets import Unicode, Dict, List, Bool, Int

class MultiNodeSpawner(DockerSpawner):
    """Enhanced spawner that supports spawning on multiple remote Docker nodes"""

    host = Unicode("tcp://0.0.0.0:2375", config=True)
    tls_config = Dict({}, config=True)

    # Service Discovery
    discovery_api_url = Unicode(
        default_value="http://localhost:15002",
        config=True,
        help="Service Discovery API URL"
    ).tag(config=True)

    # Multi-node configuration
    enable_multi_node = Bool(
        default_value=False,
        config=True,
        help="Enable spawning on multiple nodes"
    ).tag(config=True)

    worker_containers = Dict(
        default_value={},
        help="Mapping of worker node hostnames to container IDs"
    ).tag(config=True)

    # Node information
    primary_node = Dict(default_value={})
    worker_nodes = List(trait=Dict(), default_value=[])
    selected_nodes = List(trait=Dict(), default_value=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_internal_ip = False
        self._docker_clients = {}  # Cache for multiple Docker clients

    def _get_docker_client(self, host_url=None):
        """Get or create Docker client for specific host"""
        if host_url is None:
            host_url = self.host

        if host_url not in self._docker_clients:
            try:
                client = docker.APIClient(base_url=host_url, tls=self.tls_config)
                client.ping()
                self.log.info(f"[DOCKER_CLIENT] Connected to Docker: {host_url}")
                self._docker_clients[host_url] = client
            except Exception as e:
                self.log.error(f"[DOCKER_CLIENT] Failed to connect to {host_url}: {e}")
                raise

        return self._docker_clients[host_url]

    @property
    def client(self):
        """Override client property to use the primary node's Docker client"""
        return self._get_docker_client(self.host)

    async def _request_nodes_from_discovery(self):
        """Request nodes from discovery service"""
        try:
            profile_id = self.user_options.get('profile_id', 1)
            num_nodes = int(self.user_options.get('node_count_final', 1))

            # Make async request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.discovery_api_url}/select-nodes",
                    json={
                        'profile_id': int(profile_id),
                        'num_nodes': num_nodes,
                        'user_id': self.user.name
                    },
                    timeout=10
                )
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('selected_nodes', [])
            else:
                self.log.error(f"Failed to get nodes: {response.text}")
                return []

        except Exception as e:
            self.log.error(f"Error requesting nodes: {e}")
            return []

    async def start(self):
        """Start containers on selected nodes"""
        logger = logging.getLogger("jupyterhub")
        logger.info(f"[SPAWNER] user_options: {self.user_options}")

        # Get nodes from form or discovery service
        selected_nodes_json = self.user_options.get('selected_nodes', '[]')
        try:
            self.selected_nodes = json.loads(selected_nodes_json)
        except:
            self.selected_nodes = []

        # If no nodes from form, request from discovery
        if not self.selected_nodes:
            self.selected_nodes = await self._request_nodes_from_discovery()

        if not self.selected_nodes:
            # Fallback to old behavior - single node from form
            node_ip = self.user_options.get("node_ip")
            if not node_ip or node_ip in ['127.0.0.1', 'localhost', '0.0.0.0']:
                raise ValueError("No valid nodes available for spawning")

            # Create node info for compatibility
            self.selected_nodes = [{
                'hostname': self.user_options.get('node', 'unknown'),
                'ip': node_ip
            }]

        # Set primary and worker nodes
        self.primary_node = self.selected_nodes[0]
        self.worker_nodes = self.selected_nodes[1:] if len(self.selected_nodes) > 1 else []

        # Configure for primary node
        self.host = f"tcp://{self.primary_node['ip']}:2375"
        node_ip = self.primary_node['ip']

        # Image selection
        image = self.user_options.get("image", "danielcristh0/jupyterlab:cpu")
        self.image = image

        # Reset client to use new host
        self._client = None
        client = self.client  # This will create new client with updated host

        self.log.info(f"[PRIMARY_NODE] Starting on {self.primary_node['hostname']} ({node_ip})")
        self.log.info(f"[MULTI_NODE] Total nodes: {len(self.selected_nodes)}, Workers: {len(self.worker_nodes)}")

        # Hub configuration
        hub_ip = os.environ.get('JUPYTERHUB_HOST', '10.33.17.30')

        # Environment for all containers
        self.environment.update({
            'JUPYTERHUB_API_URL': f'http://{hub_ip}:18000/hub/api',
            'JUPYTERHUB_BASE_URL': '/',
            'JUPYTERHUB_SERVICE_PREFIX': f'/user/{self.user.name}/',
            'JUPYTERHUB_USER': self.user.name,
            'JUPYTERHUB_CLIENT_ID': f'jupyterhub-user-{self.user.name}',
            'JUPYTERHUB_API_TOKEN': self.api_token,
            'JUPYTERHUB_SERVICE_URL': f'http://{hub_ip}:18000',
            # Multi-node info
            'JUPYTER_NODE_TYPE': 'primary',
            'JUPYTER_NODE_HOSTNAME': self.primary_node['hostname'],
            'JUPYTER_TOTAL_NODES': str(len(self.selected_nodes)),
        })

        # Add worker nodes info to environment
        if self.worker_nodes:
            worker_hostnames = ','.join([w['hostname'] for w in self.worker_nodes])
            worker_ips = ','.join([w['ip'] for w in self.worker_nodes])
            self.environment.update({
                'JUPYTER_WORKER_NODES': worker_hostnames,
                'JUPYTER_WORKER_IPS': worker_ips
            })

        # Args for Jupyter
        self.args = [
            '--ServerApp.ip=0.0.0.0',
            '--ServerApp.port=8888',
            '--ServerApp.allow_origin=*',
            '--ServerApp.disable_check_xsrf=True',
            f'--ServerApp.base_url=/user/{self.user.name}/',
            '--ServerApp.allow_remote_access=True',
        ]

        # GPU configuration
        if any(x in image for x in ["gpu", "cu", "tf", "rpl"]):
            self.extra_host_config = {"runtime": "nvidia"}
        else:
            self.extra_host_config = {}

        self.extra_host_config.update({
            "port_bindings": {8888: None},
            "extra_hosts": {
                "hub": hub_ip,
                "jupyterhub": hub_ip
            }
        })

        # Start primary container
        self.log.info(f"[PRIMARY] Starting container with image: {self.image}")
        container_id = await super().start()

        # Wait for primary to be ready
        await asyncio.sleep(15)

        # Check primary container
        container = self.client.inspect_container(self.container_id)
        container_state = container.get("State", {})

        if not container_state.get("Running", False):
            logs = self.client.logs(self.container_id, tail=100).decode('utf-8')
            self.log.error(f"[PRIMARY] Container not running. Logs:\n{logs}")
            raise Exception(f"Primary container failed to start")

        # Get port mapping
        ports = container["NetworkSettings"]["Ports"]
        if "8888/tcp" not in ports or not ports["8888/tcp"]:
            raise Exception("Port 8888 not exposed on primary container")

        host_port = ports["8888/tcp"][0]["HostPort"]
        self.ip = node_ip
        self.port = int(host_port)
        self.server_ip = node_ip
        self.server_port = str(host_port)

        self.log.info(f"[PRIMARY] Jupyter running at http://{self.ip}:{self.port}")

        # Start worker containers if multi-node is enabled
        if self.enable_multi_node and self.worker_nodes:
            await self._start_worker_containers()

        return container_id

    async def _start_worker_containers(self):
        """Start containers on worker nodes"""
        self.log.info(f"[WORKERS] Starting {len(self.worker_nodes)} worker containers")

        tasks = []
        for worker in self.worker_nodes:
            task = self._start_worker_container(worker)
            tasks.append(task)

        # Wait for all workers
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.log.error(f"[WORKER] Failed on {self.worker_nodes[i]['hostname']}: {result}")
            else:
                self.log.info(f"[WORKER] Started on {self.worker_nodes[i]['hostname']}: {result}")

    async def _start_worker_container(self, worker_node):
        """Start a container on a worker node"""
        try:
            # Get Docker client for this worker
            worker_host = f"tcp://{worker_node['ip']}:2375"
            worker_client = self._get_docker_client(worker_host)

            # Container name
            container_name = f"{self.name}-worker-{worker_node['hostname']}"

            # Worker environment
            worker_env = self.environment.copy()
            worker_env.update({
                'JUPYTER_NODE_TYPE': 'worker',
                'JUPYTER_NODE_HOSTNAME': worker_node['hostname'],
                'JUPYTER_PRIMARY_HOST': self.primary_node['hostname'],
                'JUPYTER_PRIMARY_IP': self.primary_node['ip'],
                'JUPYTER_PRIMARY_PORT': str(self.port)
            })

            # Create worker container
            self.log.info(f"[WORKER] Creating container on {worker_node['hostname']}")

            # Container configuration
            container_config = {
                'image': self.image,
                'name': container_name,
                'environment': worker_env,
                'detach': True,
                'host_config': worker_client.create_host_config(
                    binds=self.volume_binds,
                    port_bindings={8888: None},
                    extra_hosts={
                        "hub": os.environ.get('JUPYTERHUB_HOST', '10.33.17.30'),
                        "primary": self.primary_node['ip']
                    },
                    runtime='nvidia' if 'gpu' in self.image else None
                ),
                # Worker command - can be customized
                'command': [
                    'bash', '-c',
                    'echo "Worker node ready" && sleep infinity'
                ]
            }

            # Create and start container
            container = worker_client.create_container(**container_config)
            container_id = container['Id']
            worker_client.start(container_id)

            # Store container ID
            self.worker_containers[worker_node['hostname']] = container_id

            self.log.info(f"[WORKER] Started container {container_id[:12]} on {worker_node['hostname']}")
            return container_id

        except Exception as e:
            self.log.error(f"[WORKER] Error on {worker_node['hostname']}: {e}")
            raise

    async def stop(self, now=False):
        """Stop all containers including workers"""
        self.log.info(f"[STOP] Stopping all containers for {self.user.name}")

        # Stop worker containers first
        if self.worker_containers:
            await self._stop_worker_containers()

        # Stop primary container
        try:
            await super().stop(now)
        except Exception as e:
            self.log.error(f"[STOP] Error stopping primary: {e}")

    async def _stop_worker_containers(self):
        """Stop all worker containers"""
        tasks = []

        for hostname, container_id in self.worker_containers.items():
            worker = next((w for w in self.worker_nodes if w['hostname'] == hostname), None)
            if worker:
                task = self._stop_worker_container(worker, container_id)
                tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)
        self.worker_containers.clear()

    async def _stop_worker_container(self, worker_node, container_id):
        """Stop a worker container"""
        try:
            worker_host = f"tcp://{worker_node['ip']}:2375"
            worker_client = self._get_docker_client(worker_host)

            # Stop and remove container
            worker_client.stop(container_id)
            worker_client.remove_container(container_id)

            self.log.info(f"[WORKER] Stopped container on {worker_node['hostname']}")

        except Exception as e:
            self.log.error(f"[WORKER] Error stopping on {worker_node['hostname']}: {e}")

    async def poll(self):
        """Check if all containers are running"""
        # Check primary
        try:
            primary_status = await super().poll()
            if primary_status is not None:
                return primary_status
        except Exception as e:
            self.log.error(f"[POLL] Primary poll error: {e}")
            return 1

        # Check workers if enabled
        if self.enable_multi_node and self.worker_containers:
            for hostname, container_id in self.worker_containers.items():
                worker = next((w for w in self.worker_nodes if w['hostname'] == hostname), None)
                if worker:
                    try:
                        worker_host = f"tcp://{worker['ip']}:2375"
                        worker_client = self._get_docker_client(worker_host)
                        container = worker_client.inspect_container(container_id)
                        if not container['State']['Running']:
                            self.log.warning(f"[POLL] Worker {hostname} not running")
                            return 1
                    except Exception as e:
                        self.log.error(f"[POLL] Worker {hostname} poll error: {e}")
                        return 1

        return None

    # Keep all the existing property overrides from your base.py
    @property
    def ip(self):
        if hasattr(self, 'server_ip') and self.server_ip:
            return self.server_ip
        return getattr(self, '_ip', '127.0.0.1')

    @ip.setter
    def ip(self, value):
        self._ip = value

    @property
    def port(self):
        if hasattr(self, 'server_port') and self.server_port:
            return int(self.server_port)
        return getattr(self, '_port', 8888)

    @port.setter
    def port(self, value):
        self._port = int(value)

    @property
    def url(self):
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            base_url = f"http://{self.server_ip}:{self.server_port}"
            return base_url
        return super().url

    @property
    def server_url(self):
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            url = f"http://{self.server_ip}:{self.server_port}"
            return url
        return super().server_url

    async def get_ip_and_port(self):
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            result = (self.server_ip, int(self.server_port))
            return result
        if hasattr(super(), 'get_ip_and_port') and asyncio.iscoroutinefunction(super().get_ip_and_port):
            result = await super().get_ip_and_port()
        else:
            result = (self.ip, self.port)
        return result

    def __del__(self):
        """Clean up Docker clients"""
        for client in self._docker_clients.values():
            try:
                client.close()
            except:
                pass