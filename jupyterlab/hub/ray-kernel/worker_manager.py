"""
Simple Ray Worker Manager
Spawns and manages Ray worker containers on remote nodes
"""

import docker
import asyncio
import logging
import time
import uuid
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
        self.worker_image = "danielcrist0/ray:rpl"

    def _get_docker_client(self, node_ip: str) -> docker.APIClient:
        """Get or create Docker client for a node (similar to base.py pattern)"""
        if node_ip not in self.docker_clients:
            try:
                # Follow the same pattern as base.py
                host = f"tcp://{node_ip}:2375"
                client = docker.APIClient(base_url=host, tls={})
                client.ping()
                self.docker_clients[node_ip] = client
                self.logger.info(f"[RAY_WORKER] Connected to Docker on {node_ip}")
            except Exception as e:
                self.logger.error(f"[RAY_WORKER] Failed to connect to Docker on {node_ip}: {e}")
                raise

        return self.docker_clients[node_ip]

    async def spawn_workers(self, user_name: str) -> List[Dict]:
        """Spawn Ray workers on all configured nodes"""
        spawned_workers = []

        for node_ip in self.worker_nodes:
            try:
                worker = await self._spawn_worker_on_node(node_ip, user_name)
                spawned_workers.append(worker)
                self.active_workers.append(worker)
                self.logger.info(f"[RAY_WORKER] Successfully spawned worker on {node_ip}")
            except Exception as e:
                self.logger.error(f"[RAY_WORKER] Failed to spawn worker on {node_ip}: {e}")

        return spawned_workers

    async def _spawn_worker_on_node(self, node_ip: str, user_name: str) -> Dict:
        """Spawn a single Ray worker on a specific node"""
        client = self._get_docker_client(node_ip)

        # Generate unique worker ID
        worker_id = f"ray-worker-{user_name}-{uuid.uuid4().hex[:8]}"

        # Container configuration (similar to base.py pattern)
        environment = {
            'RAY_HEAD_ADDRESS': self.ray_head_address,
            'RAY_WORKER_NODE_IP': node_ip,
            'JUPYTERHUB_USER': user_name,
        }

        # Create container config
        container_config = client.create_container_config(
            image=self.worker_image,
            environment=environment,
            command=[
                'ray', 'start',
                '--address', self.ray_head_address,
                '--node-ip-address', node_ip,
                '--block'
            ],
            name=worker_id,
            detach=True
        )

        # Host config (similar to base.py)
        host_config = client.create_host_config(
            network_mode='host',  # Use host network for Ray
            auto_remove=False,
            restart_policy={"Name": "unless-stopped"}
        )

        self.logger.info(f"[RAY_WORKER] Creating worker {worker_id} on {node_ip}")

        try:
            # Create container
            container = client.create_container(
                image=self.worker_image,
                environment=environment,
                command=[
                    'ray', 'start',
                    '--address', self.ray_head_address,
                    '--node-ip-address', node_ip,
                    '--block'
                ],
                name=worker_id,
                detach=True,
                host_config=host_config
            )

            container_id = container['Id']

            # Start container
            client.start(container_id)

            # Wait a bit and check if container is running
            await asyncio.sleep(3)

            container_info = client.inspect_container(container_id)

            if not container_info['State']['Running']:
                logs = client.logs(container_id, tail=50).decode('utf-8')
                self.logger.error(f"[RAY_WORKER] Container failed to start. Logs:\n{logs}")
                raise Exception(f"Worker container {worker_id} failed to start")

            worker_info = {
                'worker_id': worker_id,
                'container_id': container_id,
                'node_ip': node_ip,
                'status': 'running',
                'created_at': time.time(),
                'user_name': user_name,
            }

            self.logger.info(f"[RAY_WORKER] Worker {worker_id} running on {node_ip}")
            return worker_info

        except Exception as e:
            self.logger.error(f"[RAY_WORKER] Failed to create worker container {worker_id}: {e}")
            raise

    async def stop_workers(self, user_name: str = None) -> List[str]:
        """Stop Ray workers for a specific user or all workers"""
        stopped_workers = []

        workers_to_remove = []
        for i, worker in enumerate(self.active_workers):
            if user_name is None or worker.get('user_name') == user_name:
                try:
                    await self._stop_worker(worker)
                    stopped_workers.append(worker['worker_id'])
                    workers_to_remove.append(i)
                except Exception as e:
                    self.logger.error(f"[RAY_WORKER] Failed to stop worker {worker['worker_id']}: {e}")

        # Remove stopped workers from active list (reverse order to maintain indices)
        for i in reversed(workers_to_remove):
            self.active_workers.pop(i)

        return stopped_workers

    async def _stop_worker(self, worker_info: Dict):
        """Stop a single Ray worker"""
        node_ip = worker_info['node_ip']
        container_id = worker_info['container_id']
        worker_id = worker_info['worker_id']

        try:
            client = self._get_docker_client(node_ip)

            # Stop container
            client.stop(container_id, timeout=10)

            # Remove container
            client.remove_container(container_id, force=True)

            self.logger.info(f"[RAY_WORKER] Stopped and removed worker {worker_id}")

        except Exception as e:
            self.logger.error(f"[RAY_WORKER] Failed to stop worker {worker_id}: {e}")
            raise

    def get_worker_status(self) -> List[Dict]:
        """Get status of all active workers"""
        status_list = []

        for worker in self.active_workers:
            try:
                client = self._get_docker_client(worker['node_ip'])
                container_info = client.inspect_container(worker['container_id'])

                status = {
                    'worker_id': worker['worker_id'],
                    'node_ip': worker['node_ip'],
                    'status': 'running' if container_info['State']['Running'] else 'stopped',
                    'created_at': worker['created_at'],
                    'uptime': time.time() - worker['created_at'] if container_info['State']['Running'] else 0,
                }

                status_list.append(status)

            except Exception as e:
                self.logger.error(f"[RAY_WORKER] Failed to get status for worker {worker['worker_id']}: {e}")
                status_list.append({
                    'worker_id': worker['worker_id'],
                    'node_ip': worker['node_ip'],
                    'status': 'error',
                    'error': str(e)
                })

        return status_list

    async def cleanup_user_workers(self, user_name: str):
        """Cleanup all workers for a specific user"""
        return await self.stop_workers(user_name)

    def __del__(self):
        """Cleanup Docker clients"""
        for client in self.docker_clients.values():
            try:
                client.close()
            except:
                pass