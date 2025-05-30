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