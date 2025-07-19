import os
import asyncio
import logging
import docker
import json
import shutil
import uuid
from dockerspawner import DockerSpawner
from traitlets import Unicode, Dict, List

class MultiNodeSpawner(DockerSpawner):
    """
    Custom DockerSpawner to support spawning user servers across multiple nodes
    and integrate with Jupyter Enterprise Gateway.
    """

    jupyter_gateway_public_url = Unicode(
        "http://10.33.17.30:8889",
        config=True,
        help="Public URL of Jupyter Enterprise Gateway accessible from JupyterLab containers."
    ).tag(config=True)

    gateway_auth_token = Unicode('jeg-jeg-an', config=True).tag(config=True)
    kernels_dir = Unicode('/srv/jupyterhub/kernels', config=True).tag(config=True)
    server_ip = Unicode("", config=True)
    server_port = Unicode("", config=True)
    selected_nodes = List(trait=Dict(), default_value=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_internal_ip = False
        self._docker_clients = {}
        self.log.info(f"Spawner initialized with kernel directory: {self.kernels_dir}")

    @property
    def client(self):
        return self._get_docker_client(self.host)
    
    @property
    def server_url(self):
        # Override server_url to return the actual container IP:Port
        if self.server_ip and self.server_port:
            return f"http://{self.server_ip}:{self.server_port}"
        return super().server_url

    def get_env(self):
        """
        Prepare environment variables for the user container.
        """
        env = super().get_env()
        hub_host = os.environ.get('JUPYTERHUB_HUB_HOST', '10.33.17.30')
        hub_port = os.environ.get('JUPYTERHUB_HUB_PORT', '18000')
        
        all_node_ips = [str(node['ip']).strip() for node in self.selected_nodes if 'ip' in node]
        remote_hosts_str = ','.join(all_node_ips)
        
        env.update({
            'JUPYTERHUB_API_TOKEN': self.api_token,
            'JUPYTERHUB_CLIENT_ID': f'jupyterhub-user-{self.user.name}',
            'JUPYTERHUB_USER': self.user.name,
            'JUPYTERHUB_API_URL': f'http://{hub_host}:{hub_port}/hub/api',
            'KERNEL_USERNAME': 'daniel',
            'EG_REMOTE_HOSTS': remote_hosts_str
        })
        self.log.info(f"EG_REMOTE_HOSTS set to: {remote_hosts_str}")
        return env

    def _generate_kernelspecs_config(self):
        """
        Generate custom kernelspecs for each selected node to be used by JEG.
        
        Example kernel.json:
        {
            "display_name": "Python 3 on rpl-02",
            "language": "python",
            "metadata": {
                "process_proxy": {
                "class_name": "enterprise_gateway.services.processproxies.distributed.DistributedProcessProxy"
                },
                "debugger": true
            },
            "argv": [
                "docker",
                "run",
                "--rm",
                "--network=host",
                "danielcristh0/jupyterlab:cpu",
                "python3",
                "/usr/local/bin/launch_ipykernel.py",
                "--RemoteProcessProxy.kernel-id",
                "{kernel_id}",
                "--RemoteProcessProxy.response-address",
                "{response_address}",
                "--RemoteProcessProxy.public-key",
                "{public_key}",
                "--RemoteProcessProxy.port-range",
                "{port_range}",
                "--RemoteProcessProxy.spark-context-initialization-mode",
                "none"
            ],
                "env": {
                    "KERNEL_USERNAME": "daniel"
                }
            }
        """
        kernelspecs = {}
        kernel_image = self.user_options.get('image', 'elyra/kernel-py:3.2.3')
        
        for i, node in enumerate(self.selected_nodes):
            node_ip = str(node['ip']).strip()
            hostname = node.get('hostname', f'node-{i+1}')
            node_id = f"python3-docker-{hostname.lower().replace(' ', '-')}"
            display_name = f"Python 3 on {hostname}"

            launcher_script_path = "/usr/local/bin/launch_ipykernel.py"

            argv = [
                "docker", "run",
                "--rm",
                "--network=host",
                kernel_image,
                "python3",
                launcher_script_path,
                "--RemoteProcessProxy.kernel-id", "{kernel_id}",
                "--RemoteProcessProxy.response-address", "{response_address}",
                "--RemoteProcessProxy.public-key", "{public_key}",
                "--RemoteProcessProxy.port-range", "{port_range}",
                "--RemoteProcessProxy.spark-context-initialization-mode", "none",
            ]

            kernelspecs[node_id] = {
                "spec": {
                    "display_name": display_name,
                    "language": "python",
                    "metadata": {
                        "process_proxy": {
                            "class_name": "enterprise_gateway.services.processproxies.distributed.DistributedProcessProxy",
                        },
                        "debugger": True
                    },
                    "argv": argv,
                    "env": {
                        "KERNEL_USERNAME": "daniel",
                    }
                }
            }
        return kernelspecs

    def _parse_form_data(self):
        """
        Parse selected nodes and image from user options.
        """
        user_opts = self.user_options
        selected_nodes_raw = user_opts.get('selected_nodes', [])
        if isinstance(selected_nodes_raw, str) and selected_nodes_raw.strip():
            self.selected_nodes = json.loads(selected_nodes_raw)
        elif isinstance(selected_nodes_raw, list):
            self.selected_nodes = selected_nodes_raw
        return {'image': user_opts.get('image', 'danielcristh0/jupyterlab:cpu')}

    async def _write_kernelspec_files(self):
        """
        Write kernelspec JSON files to the configured directory for JEG.
        """
        kernelspecs_config = self._generate_kernelspecs_config()
        self.log.info(f"Writing {len(kernelspecs_config)} kernelspec files to {self.kernels_dir}")
        os.makedirs(self.kernels_dir, exist_ok=True)
        for kernel_id, kernelspec in kernelspecs_config.items():
            try:
                kernel_path = os.path.join(self.kernels_dir, kernel_id)
                os.makedirs(kernel_path, exist_ok=True)
                kernel_file_path = os.path.join(kernel_path, 'kernel.json')
                with open(kernel_file_path, 'w') as f:
                    json.dump(kernelspec['spec'], f, indent=2)
                self.log.info(f"Kernelspec written: {kernel_file_path}")
            except Exception as e:
                self.log.error(f"Failed to write kernelspec for {kernel_id}: {e}", exc_info=True)

    async def start(self):
        """
        Start the user JupyterLab container on the selected primary node.
        Also writes kernelspecs for remote kernel execution.
        """
        form_data = self._parse_form_data()
        if not self.selected_nodes:
            raise ValueError("No nodes selected.")
        
        primary_node = self.selected_nodes[0]
        self.host = f"tcp://{str(primary_node['ip']).strip()}:2375"
        self.image = form_data.get('image')
        self.host_ip = '0.0.0.0'

        await self._write_kernelspec_files()
        await self._start_jupyterlab_server_container(primary_node)
        
        return (self.server_ip, int(self.server_port))

    async def _start_jupyterlab_server_container(self, primary_node):
        """
        Launch the main JupyterLab UI container on the primary node.
        """
        self.args = [
            '--ServerApp.ip=0.0.0.0',
            '--ServerApp.port=8888',
            f'--ServerApp.base_url={self.server.base_url}',
            '--ServerApp.disable_check_xsrf=True',
            '--Application.log_level=DEBUG',
            '--GatewayClient.url=' + self.jupyter_gateway_public_url,
            '--GatewayClient.auth_token=' + self.gateway_auth_token
        ]
        self.extra_host_config = {'network_mode': 'jupyterhub-network'}
        _, port = await super().start()
        self.server_ip = str(primary_node['ip']).strip()
        self.server_port = str(port)

    async def stop(self, now=False):
        """
        Clean up kernelspec files when the user's server is stopped.
        """
        self.log.info(f"Removing kernelspecs for user {self.user.name}")
        kernelspecs_config = self._generate_kernelspecs_config()
        for kernel_id in kernelspecs_config.keys():
            try:
                kernel_path = os.path.join(self.kernels_dir, kernel_id)
                if os.path.isdir(kernel_path):
                    shutil.rmtree(kernel_path)
                    self.log.info(f"Removed: {kernel_path}")
            except Exception as e:
                self.log.error(f"Failed to remove {kernel_id}: {e}")
        return await super().stop(now)

    async def poll(self):
        # Check if the user container is still running.
        return await super().poll()

    def _get_docker_client(self, host_url=None):
        """
        Return a cached Docker client for the specified host.
        Creates a new one if not yet available.
        """
        host_url = host_url or self.host
        if not host_url:
            return None
        if host_url not in self._docker_clients:
            self.log.info(f"Connecting to Docker daemon at: {host_url}")
            try:
                self._docker_clients[host_url] = docker.APIClient(
                    base_url=host_url, tls=self.tls_config, timeout=10
                )
            except Exception as e:
                self.log.error(f"Error connecting to Docker at {host_url}: {e}", exc_info=True)
                raise
        return self._docker_clients[host_url]
