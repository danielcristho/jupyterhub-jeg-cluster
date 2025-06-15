import os
import asyncio
import logging
import docker
import json
import requests
from dockerspawner import DockerSpawner
from traitlets import Unicode, Dict, List, Bool

class MultiNodeSpawner(DockerSpawner):
    """
    Multi-Node Spawner
    """
    host = Unicode("tcp://0.0.0.0:2375", config=True)
    tls_config = Dict({}, config=True)

    discovery_api_url = Unicode(
        default_value="http://192.168.122.1:15002",
        config=True,
        help="Service Discovery API URL (must match form API_URL)"
    ).tag(config=True)

    # Multi-node configuration
    enable_multi_node = Bool(
        default_value=True,
        config=True,
        help="Enable spawning on multiple nodes"
    ).tag(config=True)

    # Node information
    selected_nodes = List(trait=Dict(), default_value=[])
    worker_containers = Dict(default_value={})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_internal_ip = False
        self._docker_clients = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_internal_ip = False
        self._docker_clients = {}

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
    def ip(self):
        """Force return remote server IP"""
        if hasattr(self, 'server_ip') and self.server_ip:
            self.log.info(f"[IP_OVERRIDE] Using: {self.server_ip}")
            return self.server_ip
        return getattr(self, '_ip', '127.0.0.1')

    @ip.setter
    def ip(self, value):
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
        self._port = int(value)

    @property
    def client(self):
        """Override client property to ensure use the updated Docker client"""
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

    async def get_ip_and_port(self):
        """Override to return remote server IP and port"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            result = (self.server_ip, int(self.server_port))
            self.log.info(f"[GET_IP_PORT_OVERRIDE] Using: {result}")
            return result
        
        # Try to get from _ip and _port if available
        if hasattr(self, '_ip') and hasattr(self, '_port') and self._ip and self._port:
            result = (self._ip, int(self._port))
            self.log.info(f"[GET_IP_PORT_FALLBACK] Using fallback: {result}")
            return result

        # Last resort - call parent method
        if hasattr(super(), 'get_ip_and_port') and asyncio.iscoroutinefunction(super().get_ip_and_port):
            result = await super().get_ip_and_port()
        else:
            result = (self.ip, self.port)

        self.log.info(f"[GET_IP_PORT_DEFAULT] Using: {result}")
        
        if result[0] is None or result[1] is None:
            self.log.error(f"[GET_IP_PORT_ERROR] Got None values: {result}")
            raise ValueError(f"IP or port is None: ip={result[0]}, port={result[1]}")
            
        return result

    def _get_ip_and_port(self):
        """CRITICAL FIX: Override sync version with robust handling"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            ip = str(self.server_ip).strip()
            port = int(self.server_port)
            self.log.info(f"[_GET_IP_PORT_SERVER] Returning server values: ({ip}, {port})")
            return (ip, port)
            
        if hasattr(self, '_ip') and hasattr(self, '_port') and self._ip and self._port:
            ip = str(self._ip).strip()
            port = int(self._port)
            self.log.info(f"[_GET_IP_PORT_FALLBACK] Returning fallback values: ({ip}, {port})")
            return (ip, port)
            
        try:
            result = super()._get_ip_and_port() if hasattr(super(), '_get_ip_and_port') else (self.ip, self.port)
            
            if result and len(result) == 2 and result[0] and result[1]:
                ip = str(result[0]).strip()
                port = int(result[1])
                if ip and ip != 'None':
                    self.log.info(f"[_GET_IP_PORT_PARENT] Returning parent values: ({ip}, {port})")
                    return (ip, port)
        except Exception as e:
            self.log.error(f"[_GET_IP_PORT_PARENT_ERROR] Parent method failed: {e}")
        
        # Emergency fallback
        emergency_ip = '127.0.0.1'
        emergency_port = 8888
        self.log.error(f"[_GET_IP_PORT_EMERGENCY] Using emergency fallback: ({emergency_ip}, {emergency_port})")
        return (emergency_ip, emergency_port)

    @property
    def url(self):
        """Override URL to ensure it points to remote server"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            base_url = f"http://{self.server_ip}:{self.server_port}"
            self.log.info(f"[URL_OVERRIDE] Using URL: {base_url}")
            return base_url
        
        if hasattr(self, '_ip') and hasattr(self, '_port'):
            fallback_url = f"http://{self._ip}:{self._port}"
            self.log.info(f"[URL_FALLBACK] Using fallback URL: {fallback_url}")
            return fallback_url
            
        return super().url

    @property
    def server_url(self):
        """Override server_url to ensure consistency"""
        if hasattr(self, 'server_ip') and hasattr(self, 'server_port') and self.server_ip and self.server_port:
            url = f"http://{self.server_ip}:{self.server_port}"
            self.log.info(f"[SERVER_URL_OVERRIDE] Using server_url: {url}")
            return url
            
        # Fallback to constructed URL
        if hasattr(self, '_ip') and hasattr(self, '_port') and self._ip and self._port:
            url = f"http://{self._ip}:{self._port}"
            self.log.info(f"[SERVER_URL_FALLBACK] Using fallback server_url: {url}")
            return url
            
        try:
            url = super().server_url
            self.log.info(f"[SERVER_URL_PARENT] Using parent server_url: {url}")
            return url
        except Exception as e:
            self.log.error(f"[SERVER_URL_ERROR] Parent server_url failed: {e}")
            ip = getattr(self, 'ip', '127.0.0.1')
            port = getattr(self, 'port', 8888)
            fallback_url = f"http://{ip}:{port}"
            self.log.warning(f"[SERVER_URL_MANUAL] Using manual fallback: {fallback_url}")
            return fallback_url

    def create_object(self):
        """Override container creation to force correct port binding"""
        if not hasattr(self, 'extra_host_config'):
            self.extra_host_config = {}

        self.extra_host_config['port_bindings'] = {8888: None}
        self.extra_host_config['publish_all_ports'] = True
        self.extra_host_config.pop('network_mode', None)
        self.log.info(f"[CREATE_OBJECT] Final extra_host_config: {self.extra_host_config}")

        return super().create_object()

    def _parse_form_data(self):
        """Parse data from your HTML form - FIXED VERSION"""
        logger = logging.getLogger("jupyterhub")
        logger.info(f"[FORM_DATA] Raw user_options: {self.user_options}")
        
        logger.info(f"[DEBUG] user_options type: {type(self.user_options)}")
        logger.info(f"[DEBUG] user_options keys: {list(self.user_options.keys()) if isinstance(self.user_options, dict) else 'NOT_DICT'}")

        # Extract form data
        form_data = {
            'profile_id': self.user_options.get('profile_id'),
            'profile_name': self.user_options.get('profile_name'),
            'image': self.user_options.get('image', 'danielcristh0/jupyterlab:cpu'),
            'selected_nodes_raw': self.user_options.get('selected_nodes'),  # This is now a list from options_from_form
            'primary_node': self.user_options.get('primary_node'),
            'node_count_final': int(self.user_options.get('node_count_final', 1)),

            'node_ip': self.user_options.get('node_ip'),
            'node': self.user_options.get('node', 'unknown'),
        }
        
        logger.info(f"[DEBUG] Extracted form_data: {form_data}")
        logger.info(f"[DEBUG] selected_nodes_raw: {form_data['selected_nodes_raw']} (type: {type(form_data['selected_nodes_raw'])})")

        selected_nodes_raw = form_data['selected_nodes_raw']
        
        if isinstance(selected_nodes_raw, list):
            self.selected_nodes = selected_nodes_raw
            logger.info(f"[FORM_DATA] Using pre-processed list: {len(self.selected_nodes)} nodes")
        elif isinstance(selected_nodes_raw, str) and selected_nodes_raw.strip():
            try:
                self.selected_nodes = json.loads(selected_nodes_raw)
                logger.info(f"[FORM_DATA] Parsed JSON fallback: {len(self.selected_nodes)} nodes")
            except (json.JSONDecodeError, TypeError) as e:
                self.selected_nodes = []
                logger.warning(f"[FORM_DATA] Could not parse JSON fallback: {e}")
        else:
            self.selected_nodes = []
            logger.warning(f"[FORM_DATA] No valid selected_nodes data")

        # Legacy fallback
        if not self.selected_nodes and form_data['node_ip']:
            legacy_node = {
                'hostname': form_data['node'] or 'legacy-node',
                'ip': form_data['node_ip']
            }
            self.selected_nodes = [legacy_node]
            logger.info(f"[FORM_DATA] Using legacy single node: {form_data['node_ip']}")

        # Final validation
        validated_nodes = []
        for i, node in enumerate(self.selected_nodes):
            if isinstance(node, dict) and 'ip' in node:
                # Ensure hostname exists
                if 'hostname' not in node:
                    node['hostname'] = f"node-{i}"
                validated_nodes.append(node)
                logger.info(f"[DEBUG] Node {i} validated: {node.get('hostname')} ({node.get('ip')})")
            else:
                logger.warning(f"[DEBUG] Node {i} INVALID: {node}")

        self.selected_nodes = validated_nodes
        logger.info(f"[DEBUG] FINAL selected_nodes: {len(self.selected_nodes)} validated nodes")

        return form_data

    async def start(self):
        logger = logging.getLogger("jupyterhub")

        form_data = self._parse_form_data()

        if not self.selected_nodes:
            raise ValueError("No nodes selected. Please select nodes in the form or check service discovery.")

        logger.info(f"[SPAWNER] Starting with {len(self.selected_nodes)} nodes")
        logger.info(f"[SPAWNER] Profile: {form_data['profile_name']} (ID: {form_data['profile_id']})")
        logger.info(f"[SPAWNER] Image: {form_data['image']}")

        primary_node = self.selected_nodes[0]
        await self._start_primary_container(primary_node, form_data)

        if self.enable_multi_node and len(self.selected_nodes) > 1:
            await self._start_worker_containers(form_data)

        final_ip = getattr(self, 'server_ip', getattr(self, '_ip', '127.0.0.1'))
        final_port = int(getattr(self, 'server_port', getattr(self, '_port', 8888)))
        
        logger.info(f"[SPAWNER] Returning IP/Port to JupyterHub: ({final_ip}, {final_port})")
        
        if not final_ip or final_ip.strip() == '':
            final_ip = '127.0.0.1'
        
        logger.info(f"[SPAWNER] Final return values: ip='{final_ip}' ({type(final_ip)}), port={final_port} ({type(final_port)})")
        
        return (str(final_ip), int(final_port))

    async def _start_primary_container(self, primary_node, form_data):
        """Start primary container using your proven logic - FIXED VERSION"""
        
        logger = logging.getLogger("jupyterhub")
        logger.info(f"[DEBUG] primary_node data: {primary_node}")
        logger.info(f"[DEBUG] primary_node type: {type(primary_node)}")
        
        # Validate primary_node
        if not primary_node:
            raise ValueError("Primary node is None or empty")
        
        if not isinstance(primary_node, dict):
            raise ValueError(f"Primary node must be dict, got: {type(primary_node)}")
        
        if 'ip' not in primary_node:
            raise ValueError(f"Primary node missing 'ip' key. Available keys: {list(primary_node.keys())}")
        
        node_ip = str(primary_node['ip']).strip()
        logger.info(f"[DEBUG] Extracted and cleaned node_ip: '{node_ip}'")
        
        # Validate IP address
        if not node_ip:
            raise ValueError(f"Node IP is empty: {repr(primary_node['ip'])}")
        
        image = form_data['image']
        logger.info(f"[DEBUG] Using image from form: '{image}'")
        
        if not image or image.strip() == '':
            image = 'danielcristh0/jupyterlab:cpu'  # Default fallback
            logger.warning(f"[DEBUG] Empty image, using default: {image}")
        
        image = image.strip()  # Clean whitespace
        logger.info(f"[DEBUG] Final cleaned image: '{image}'")

        # Set Docker host
        new_host = f"tcp://{node_ip}:2375"
        logger.info(f"[DEBUG] Setting Docker host from '{self.host}' to '{new_host}'")
        
        self.host = new_host
        self.tls_config = {}
        self.use_internal_ip = False
        self.image = image  # Set the cleaned image
        self._client = None  # Force recreation

        # Test Docker connection
        try:
            client = self.client
            logger.info(f"[DEBUG] Docker client created: {client.base_url}")
            client.ping()
            logger.info(f"[DEBUG] Docker ping successful to: {client.base_url}")
        except Exception as e:
            logger.error(f"[DEBUG] Docker connection failed to {new_host}: {e}")
            raise ValueError(f"Cannot connect to Docker daemon at {new_host}: {e}")

        self.log.info(f"[PRIMARY] Starting on {primary_node.get('hostname', 'unknown')} ({node_ip})")
        self.log.info(f"[PRIMARY] Docker client: {client.base_url}")
        self.log.info(f"[PRIMARY] Using image: {self.image}")  # Log the actual image being used

        # Hub configuration
        hub_ip = "192.168.122.1"

        # CRITICAL FIX: Set image as user option to bypass validation
        self.user_options['image'] = image
        self.log.info(f"[DEBUG] Set user_options image to: {self.user_options.get('image')}")

        # Environment variables
        self.environment.update({
            'JUPYTERHUB_API_URL': f'http://{hub_ip}:18000/hub/api',  # Fixed port
            'JUPYTERHUB_BASE_URL': '/',
            'JUPYTERHUB_SERVICE_PREFIX': f'/user/{self.user.name}/',
            'JUPYTERHUB_USER': self.user.name,
            'JUPYTERHUB_CLIENT_ID': f'jupyterhub-user-{self.user.name}',
            'JUPYTERHUB_API_TOKEN': self.api_token,
            'JUPYTERHUB_SERVICE_URL': f'http://{hub_ip}:18000',  # Fixed port

            # Multi-node metadata
            'JUPYTER_NODE_TYPE': 'primary',
            'JUPYTER_NODE_HOSTNAME': primary_node.get('hostname', 'unknown'),
            'JUPYTER_TOTAL_NODES': str(len(self.selected_nodes)),
            'JUPYTER_PROFILE_NAME': form_data.get('profile_name', 'unknown'),
            'JUPYTER_PROFILE_ID': str(form_data.get('profile_id', 1)),
        })

        # Add Ray configuration for multi-node
        if len(self.selected_nodes) > 1:
            worker_ips = ','.join([n['ip'] for n in self.selected_nodes[1:]])
            worker_hostnames = ','.join([n.get('hostname', f'worker-{i}') for i, n in enumerate(self.selected_nodes[1:])])

            self.environment.update({
                'RAY_ENABLED': 'true',
                'RAY_HEAD_NODE': node_ip,
                'RAY_DASHBOARD_HOST': '0.0.0.0',
                'RAY_DASHBOARD_PORT': '8265',
                'JUPYTER_WORKER_IPS': worker_ips,
                'JUPYTER_WORKER_HOSTNAMES': worker_hostnames,
            })
            self.log.info(f"[RAY] Configured Ray head node: {node_ip}")
        else:
            self.environment.update({
                'RAY_ENABLED': 'false'
            })

        # Jupyter configuration
        self.args = [
            '--ServerApp.ip=0.0.0.0',
            '--ServerApp.port=8888',
            '--ServerApp.allow_origin=*',
            '--ServerApp.disable_check_xsrf=True',
            f'--ServerApp.base_url=/user/{self.user.name}/',
            '--ServerApp.allow_remote_access=True',
        ]

        # GPU configuration
        if any(x in image.lower() for x in ["gpu", "cuda", "tensorflow-gpu"]):
            self.extra_host_config = {"runtime": "nvidia"}
            self.log.info(f"[GPU] Enabled GPU support for image: {image}")
        else:
            self.extra_host_config = {}

        self.extra_host_config.update({
            "port_bindings": {8888: None},
            "extra_hosts": {
                "hub": hub_ip,
                "jupyterhub": hub_ip
            }
        })

        self.log.info(f"[PRIMARY] About to start container with image: {self.image}")

        # CRITICAL FIX: Set default image before calling super().start() to avoid validation issues
        original_default_image = getattr(self, 'default_image', None)
        self.default_image = image
        
        # Also set the image attribute directly
        self._image = image
        
        self.log.info(f"[DEBUG] Set default_image to: {self.default_image}")

        # Start container
        try:
            container_id = await super().start()
            self.log.info(f"[PRIMARY] Container spawned: {container_id}")
        finally:
            # Restore original default_image if it existed
            if original_default_image is not None:
                self.default_image = original_default_image

        # Wait for container to start
        await asyncio.sleep(15)

        # Validate container status
        container = self.client.inspect_container(self.container_id)
        container_state = container.get("State", {})

        if not container_state.get("Running", False):
            try:
                logs = self.client.logs(self.container_id, tail=100, stdout=True, stderr=True).decode('utf-8')
                self.log.error(f"[ERROR] Container not running. Full logs:\n{logs}")
            except Exception as e:
                self.log.error(f"[ERROR] Could not get container logs: {e}")
            raise Exception(f"Container failed to start. Status: {container_state}")

        # Get port mapping
        ports = container["NetworkSettings"]["Ports"]
        if "8888/tcp" not in ports or not ports["8888/tcp"]:
            logs = self.client.logs(self.container_id, tail=50).decode('utf-8')
            self.log.error(f"[ERROR] Port 8888 not exposed. Container logs:\n{logs}")
            raise Exception("Port 8888 not exposed or not found")

        host_port = ports["8888/tcp"][0]["HostPort"]
        
        # CRITICAL FIX: Set all IP/port attributes consistently
        self._ip = node_ip
        self._port = int(host_port)
        self.server_ip = node_ip
        self.server_port = str(host_port)
        
        # Also set the properties directly for JupyterHub
        self.ip = node_ip
        self.port = int(host_port)
        
        self.log.info(f"[PRIMARY] All IP/port attributes set:")
        self.log.info(f"[PRIMARY] - self._ip: {self._ip}")
        self.log.info(f"[PRIMARY] - self._port: {self._port}")
        self.log.info(f"[PRIMARY] - self.ip: {self.ip}")
        self.log.info(f"[PRIMARY] - self.port: {self.port}")
        self.log.info(f"[PRIMARY] - self.server_ip: {self.server_ip}")
        self.log.info(f"[PRIMARY] - self.server_port: {self.server_port}")

        self.log.info(f"[PRIMARY] Jupyter running at http://{self.ip}:{self.port}")

    async def _start_worker_containers(self, form_data):
        """Start worker containers on additional nodes"""
        worker_nodes = self.selected_nodes[1:]
        self.log.info(f"[WORKERS] Starting {len(worker_nodes)} worker containers")

        for i, worker_node in enumerate(worker_nodes):
            try:
                await self._start_single_worker(worker_node, i, form_data)
            except Exception as e:
                self.log.error(f"[WORKER] Failed to start on {worker_node.get('hostname', 'unknown')}: {e}")
                # Continue with other workers even if one fails

    async def _start_single_worker(self, worker_node, worker_index, form_data):
        """Start a single worker container"""
        worker_host = f"tcp://{worker_node['ip']}:2375"
        worker_client = self._get_docker_client(worker_host)

        # CRITICAL FIX: Ensure container name is valid
        base_name = getattr(self, 'name', f'jupyterlab-{self.user.name}')
        if not base_name or base_name.strip() == '':
            base_name = f'jupyterlab-{self.user.name}'
        
        container_name = f"{base_name}-worker-{worker_index}"
        self.log.info(f"[WORKER] Creating container: {container_name}")

        # Worker environment (inherit from primary + worker-specific vars)
        worker_env = self.environment.copy()
        worker_env.update({
            'JUPYTER_NODE_TYPE': 'worker',
            'JUPYTER_NODE_HOSTNAME': worker_node.get('hostname', f'worker-{worker_index}'),
            'JUPYTER_WORKER_INDEX': str(worker_index),
            'JUPYTER_PRIMARY_IP': self.selected_nodes[0]['ip'],
            'JUPYTER_PRIMARY_PORT': str(self.port),
            'RAY_ADDRESS': f"{self.selected_nodes[0]['ip']}:10001",  # Connect to Ray head
        })

        # Container configuration
        container_config = {
            'image': self.image,
            'name': container_name,
            'environment': worker_env,
            'detach': True,
            'host_config': worker_client.create_host_config(
                binds=self.volume_binds,
                extra_hosts={
                    "hub": "192.168.122.1",
                    "primary": self.selected_nodes[0]['ip']
                },
                runtime='nvidia' if 'gpu' in self.image.lower() else None
            ),
            'command': None
        }

        # Create and start container
        container = worker_client.create_container(**container_config)
        container_id = container['Id']
        worker_client.start(container_id)

        self.worker_containers[worker_node.get('hostname', f'worker-{worker_index}')] = {
            'container_id': container_id,
            'node_ip': worker_node['ip'],
            'client': worker_client,
            'worker_index': worker_index
        }

        self.log.info(f"[WORKER] Started {container_name} on {worker_node.get('hostname', f'worker-{worker_index}')}")

    async def stop(self, now=False):
        """Stop all containers including workers"""
        self.log.info(f"[STOP] Stopping all containers for {self.user.name}")

        # Stop worker containers first
        for hostname, worker_info in list(self.worker_containers.items()):
            try:
                client = worker_info['client']
                container_id = worker_info['container_id']
                client.stop(container_id)
                client.remove_container(container_id)
                self.log.info(f"[WORKER] Stopped container on {hostname}")
            except Exception as e:
                self.log.error(f"[WORKER] Error stopping on {hostname}: {e}")

        self.worker_containers.clear()

        try:
            return await super().stop(now)
        except Exception as e:
            self.log.error(f"[SPAWNER] Stop failed: {e}")

    async def poll(self):
        """Poll all containers"""
        try:
            # Check primary container
            primary_status = await super().poll()
            if primary_status is not None:
                return primary_status

            # Check worker containers
            for hostname, worker_info in self.worker_containers.items():
                try:
                    client = worker_info['client']
                    container_id = worker_info['container_id']
                    container = client.inspect_container(container_id)
                    if not container['State']['Running']:
                        self.log.warning(f"[POLL] Worker {hostname} not running")
                        return 1
                except Exception as e:
                    self.log.error(f"[POLL] Worker {hostname} poll error: {e}")
                    return 1

            return None
        except Exception as e:
            self.log.error(f"[SPAWNER] Poll failed: {e}")
            return 1

    def __del__(self):
        """Clean up Docker clients"""
        if hasattr(self, '_client'):
            try:
                self._client.close()
            except:
                pass

        for client in self._docker_clients.values():
            try:
                client.close()
            except:
                pass