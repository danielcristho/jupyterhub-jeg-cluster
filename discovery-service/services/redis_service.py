import json
import logging
from typing import Dict, List, Optional
from redis import ConnectionPool, Redis
from config import Config

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.pool = None
        self.client = None
        self._connect()

    def _connect(self):
        """Establish Redis connection"""
        try:
            self.pool = ConnectionPool(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                password=Config.REDIS_PASSWORD,
                decode_responses=True
            )
            self.client = Redis(connection_pool=self.pool)
            self.client.ping()
            logger.info(f"Connected to Redis at {Config.REDIS_HOST}:{Config.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False

    def set_node_info(self, hostname: str, data: dict) -> bool:
        """Store node information in Redis"""
        if not self.client:
            return False

        try:
            self.client.set(
                f"node:{hostname}:info",
                json.dumps(data),
                ex=Config.REDIS_EXPIRE_SECONDS
            )
            # Also store IP separately for compatibility
            if 'ip' in data:
                self.client.set(
                    f"node:{hostname}:ip",
                    data['ip'],
                    ex=Config.REDIS_EXPIRE_SECONDS
                )
            return True
        except Exception as e:
            logger.error(f"Error storing node info: {e}")
            return False

    def get_node_info(self, hostname: str) -> Optional[Dict]:
        """Retrieve node information from Redis"""
        if not self.client:
            return None

        try:
            data = self.client.get(f"node:{hostname}:info")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving node info: {e}")
            return None

    def get_all_node_keys(self) -> List[str]:
        """Get all node keys from Redis"""
        if not self.client:
            return []

        try:
            return self.client.keys("node:*:info")
        except Exception as e:
            logger.error(f"Error getting node keys: {e}")
            return []

    def get_node_ttl(self, hostname: str) -> int:
        """Get TTL for a node"""
        if not self.client:
            return -1

        try:
            return self.client.ttl(f"node:{hostname}:info")
        except:
            return -1

    def delete_node(self, hostname: str) -> bool:
        """Delete node information from Redis"""
        if not self.client:
            return False

        try:
            self.client.delete(f"node:{hostname}:info")
            self.client.delete(f"node:{hostname}:ip")
            return True
        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            return False

    def get_all_nodes_data(self) -> List[Dict]:
        """Get all nodes data from Redis"""
        if not self.client:
            return []

        nodes = []
        for key in self.get_all_node_keys():
            ttl = self.client.ttl(key)
            if ttl <= 0:
                continue

            try:
                data = json.loads(self.client.get(key))
                nodes.append(data)
            except Exception as e:
                logger.warning(f"Failed to parse {key}: {e}")

        return nodes