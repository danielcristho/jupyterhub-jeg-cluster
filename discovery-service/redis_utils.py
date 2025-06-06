from redis import ConnectionPool, Redis
import json
import logging
from config import Config

logger = logging.getLogger("DiscoveryAPI.Redis")

class RedisManager:
    def __init__(self):
        self.redis_client = None
        self.pool = None
        self.connect()

    def connect(self):
        """Initialize Redis connection"""
        try:
            self.pool = ConnectionPool(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                password=Config.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client = Redis(connection_pool=self.pool)
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {Config.REDIS_HOST}:{Config.REDIS_PORT}")
        except Exception as e:
            self.redis_client = None
            logger.error(f"Failed to connect to Redis: {e}")

    def is_connected(self):
        """Check if Redis is connected"""
        return self.redis_client is not None

    def store_node_info(self, hostname, data):
        """Store node information in Redis"""
        if not self.redis_client:
            raise Exception("Redis not available")

        try:
            info_key = f"node:{hostname}:info"
            ip_key = f"node:{hostname}:ip"

            self.redis_client.set(info_key, json.dumps(data), ex=Config.REDIS_EXPIRE_SECONDS)
            if data.get("ip"):
                self.redis_client.set(ip_key, data["ip"], ex=Config.REDIS_EXPIRE_SECONDS)

            return True
        except Exception as e:
            logger.error(f"Failed to store node info: {e}")
            return False

    def get_node_info(self, hostname):
        """Get specific node information"""
        if not self.redis_client:
            return None

        try:
            info_key = f"node:{hostname}:info"
            data = self.redis_client.get(info_key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to get node info: {e}")
            return None

    def get_all_nodes(self, filtered=False, strict_filter=False):
        """Get all nodes from Redis with optional filtering"""
        if not self.redis_client:
            return []

        try:
            result = []
            for key in self.redis_client.keys("node:*:info"):
                ttl = self.redis_client.ttl(key)
                if ttl <= 0:
                    continue

                try:
                    data = json.loads(self.redis_client.get(key))
                    node = self._format_node_data(data)
                    result.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse {key}: {e}")

            if filtered:
                result = self._filter_nodes(result, strict_filter)

            return result
        except Exception as e:
            logger.error(f"Error in get_all_nodes: {e}")
            return []

    def _format_node_data(self, data):
        """Format node data consistently"""
        return {
            "hostname": data.get("hostname"),
            "ip": data.get("ip"),
            "cpu": data.get("cpu", 0),
            "ram_gb": data.get("ram_gb", 0),
            "has_gpu": data.get("has_gpu", False),
            "gpu": data.get("gpu", []),
            "cpu_usage_percent": data.get("cpu_usage_percent", 100),
            "memory_usage_percent": data.get("memory_usage_percent", 100),
            "disk_usage_percent": data.get("disk_usage_percent", 100),
            "active_jupyterlab": data.get("active_jupyterlab", 0),
            "active_ray": data.get("active_ray", 0),
            "total_containers": data.get("total_containers", 0),
            "last_updated": data.get("last_updated"),
        }

    def _filter_nodes(self, nodes, strict_filter=False):
        """Filter nodes based on criteria"""
        if strict_filter:
            return [
                n for n in nodes
                if (n["cpu_usage_percent"] < 60 and
                    n["memory_usage_percent"] < 60 and
                    (n["active_jupyterlab"] + n["active_ray"]) < 5)
            ]
        else:
            return [
                n for n in nodes
                if (n["cpu_usage_percent"] < 80 and
                    n["memory_usage_percent"] < 85)
            ]

    def get_debug_info(self):
        """Get Redis debug information"""
        if not self.redis_client:
            return {"error": "Redis not available"}

        try:
            all_keys = self.redis_client.keys("*")
            node_keys = self.redis_client.keys("node:*")
            info_keys = self.redis_client.keys("node:*:info")
            ip_keys = self.redis_client.keys("node:*:ip")

            debug_info = {
                "redis_connected": True,
                "total_keys": len(all_keys),
                "all_keys": all_keys,
                "node_keys": node_keys,
                "info_keys": info_keys,
                "ip_keys": ip_keys
            }

            # Get node data details
            node_data = {}
            for key in info_keys:
                data = self.redis_client.get(key)
                ttl = self.redis_client.ttl(key)
                node_data[key] = {
                    "data": data,
                    "ttl": ttl,
                    "parsed": json.loads(data) if data else None
                }
            debug_info["node_data"] = node_data

            # Get IP data
            ip_data = {}
            for key in ip_keys:
                ip = self.redis_client.get(key)
                ttl = self.redis_client.ttl(key)
                ip_data[key] = {
                    "ip": ip,
                    "ttl": ttl
                }
            debug_info["ip_data"] = ip_data

            return debug_info
        except Exception as e:
            return {"error": f"Redis debug error: {str(e)}"}

# Global Redis manager instance
redis_manager = RedisManager()