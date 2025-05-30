"""
Simple Ray Worker Manager
Spawns and manages Ray worker containers on remote nodes
"""

import docker
import asyncio
import logging
import time
from typing import List, Dict, Optional

class RayWorkerManager:
    """Manages Ray worker containers across multiple nodes"""

    def __init__(self, ray_head_address: str, worker_nodes: List[str], logger: Optional[logging.Logger] = None):
        self.ray_head_address = ray_head_address
        self.worker_nodes = worker_nodes
        self.logger = logger or logging.getLogger(__name__)

        # Docker clients for each node
        self.docker_clients: Dict[str, docker.APIClient] = {}

        # Active workers tracking
        self.active_workers: List[Dict] = []

        # Configuration
        self.worker_image = "danielcristh0/ray:rpl"
        self.max_workers_per_node = 1

    async def spawn_workers(self, user_name: str) -> List[Dict]:
        """Spawn Ray workers on all configured nodes"""
        self.logger.info(f"Spawning Ray workers for user: {user_name}")

        # Create spawn tasks for each node
        tasks = []
        for i, node_ip in enumerate(self.worker_nodes):
            task = self._spawn_worker_on_node(node_ip, user_name, i)
            tasks.append(task)

        # Execute all spawn tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful spawns
        successful_workers = []
        for result in results:
            if isinstance(result, dict):
                successful_workers.append(result)
                self.active_workers.append(result)
            else:
                self.logger.error(f"Worker spawn failed: {result}")

        self.logger.info(f"Successfully spawned {len(successful_workers)} out of {len(self.worker_nodes)} workers")
        return successful_workers

    async def _spawn_worker_on_node(self, node_ip: str, user_name: str, worker_id: int) -> Dict:
        """Spawn a single Ray worker on a specific node"""
        try:
            # Get Docker client for this node
            client = await self._get_docker_client(node_ip)

            # Container configuration
            container_name = f"ray-worker-{user_name}-{worker_id}"

            # Remove existing container if it exists
            await self._cleanup_existing_container(client, container_name)

            # Create worker container
            container_config = {
                'image': self.worker_image,
                'name': container_name,
                'command': [
                    'ray', 'start',
                    '--address', self.ray_head_address,
                    '--block'  # Keep container running
                ],
                'environment': {
                    'RAY_HEAD_ADDRESS': self.ray_head_address,
                    'RAY_WORKER_ID': str(worker_id),
                    'RAY_USER': user_name,
                    'RAY_DISABLE_IMPORT_WARNING': '1'
                },
                'detach': True,
                'restart_policy': {'Name': 'unless-stopped'},
                'labels': {
                    'ray-cluster': 'worker',
                    'ray-user': user_name,
                    'worker-id': str(worker_id),
                    'managed-by': 'jupyterhub-ray-kernel'
                },
                'host_config': {
                    'shm_size': '1G',  # Shared memory for Ray
                    'mem_limit': '2G',  # Memory limit
                }
            }

            self.logger.info(f"Creating Ray worker {worker_id} on {node_ip}")

            # Create and start container
            container = client.create_container(**container_config)
            client.start(container['Id'])

            # Wait a moment for startup
            await asyncio.sleep(3)

            # Verify container is running
            container_info = client.inspect_container(container['Id'])
            if not container_info['State']['Running']:
                raise Exception(f"Container failed to start: {container_info['State']}")

            worker_info = {
                'container_id': container['Id'],
                'container_name': container_name,
                'node_ip': node_ip,
                'worker_id': worker_id,
                'status': 'running',
                'created_at': time.time()
            }

            self.logger.info(f"✅ Ray worker {worker_id} started on {node_ip}: {container['Id'][:12]}")
            return worker_info

        except Exception as e:
            self.logger.error(f"❌ Failed to spawn worker {worker_id} on {node_ip}: {e}")
            raise e

    async def _get_docker_client(self, node_ip: str) -> docker.APIClient:
        """Get or create Docker client for a node"""
        if node_ip not in self.docker_clients:
            try:
                client = docker.APIClient(base_url=f"tcp://{node_ip}:2375")
                client.ping()  # Test connection
                self.docker_clients[node_ip] = client
                self.logger.debug(f"Connected to Docker on {node_ip}")
            except Exception as e:
                raise Exception(f"Failed to connect to Docker on {node_ip}: {e}")

        return self.docker_clients[node_ip]

    async def _cleanup_existing_container(self, client: docker.APIClient, container_name: str):
        """Remove existing container with same name"""
        try:
            existing_container = client.inspect_container(container_name)
            client.remove_container(container_name, force=True)
            self.logger.info(f"Removed existing container: {container_name}")
        except docker.errors.NotFound:
            pass  # Container doesn't exist, which is fine
        except Exception as e:
            self.logger.warning(f"Failed to cleanup existing container {container_name}: {e}")

    async def stop_workers(self, user_name: str) -> None:
        """Stop all Ray workers for a user"""
        self.logger.info(f"Stopping Ray workers for user: {user_name}")

        # Create stop tasks for all active workers
        tasks = []
        for worker in self.active_workers[:]:  # Copy list to avoid modification during iteration
            task = self._stop_single_worker(worker)
            tasks.append(task)

        # Execute all stop tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clear active workers list
        self.active_workers = []
        self.logger.info(f"Stopped all Ray workers for user: {user_name}")

    async def _stop_single_worker(self, worker_info: Dict) -> None:
        """Stop a single Ray worker"""
        try:
            node_ip = worker_info['node_ip']
            container_id = worker_info['container_id']
            worker_id = worker_info['worker_id']

            client = self.docker_clients.get(node_ip)
            if not client:
                self.logger.warning(f"No Docker client for node {node_ip}")
                return

            # Stop and remove container
            client.stop(container_id, timeout=10)
            client.remove_container(container_id, force=True)

            self.logger.info(f"Stopped Ray worker {worker_id} on {node_ip}")

        except Exception as e:
            self.logger.error(f"Failed to stop worker {worker_info}: {e}")

    def get_worker_status(self) -> List[Dict]:
        """Get status of all active Ray workers"""
        status_list = []

        for worker in self.active_workers:
            try:
                node_ip = worker['node_ip']
                container_id = worker['container_id']

                client = self.docker_clients.get(node_ip)
                if not client:
                    status_list.append({
                        **worker,
                        'status': 'no_client',
                        'running': False
                    })
                    continue

                # Get container status
                container_info = client.inspect_container(container_id)
                uptime = time.time() - worker['created_at']

                status_list.append({
                    **worker,
                    'status': container_info['State']['Status'],
                    'running': container_info['State']['Running'],
                    'uptime': uptime
                })

            except docker.errors.NotFound:
                status_list.append({
                    **worker,
                    'status': 'not_found',
                    'running': False
                })
            except Exception as e:
                status_list.append({
                    **worker,
                    'status': 'error',
                    'running': False,
                    'error': str(e)
                })

        return status_list

    def cleanup(self):
        """Cleanup Docker clients"""
        for client in self.docker_clients.values():
            try:
                client.close()
            except Exception:
                pass

        self.docker_clients = {}
        self.active_workers = []