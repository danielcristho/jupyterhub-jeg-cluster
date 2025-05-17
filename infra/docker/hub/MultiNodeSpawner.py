from dockerspawner import DockerSpawner
import redis
import os
import logging

class MultiNodeSpawner(DockerSpawner):
    def start(self):
        logger = logging.getLogger("jupyterhub")

        node = self.user_options.get("node", "")
        image = self.user_options.get("image", "danielcristh0/jupyterlab:cpu")

        # --- Redis Discovery ---
        redis_host = os.environ.get("REDIS_HOST", "redis")
        redis_port = int(os.environ.get("REDIS_PORT", 6379))
        redis_user = os.environ.get("REDIS_USER", "redis")
        redis_pass = os.environ.get("REDIS_PASSWORD", "redis@pass")
        redis_prefix = os.environ.get("REDIS_DISCOVERY_KEY_PREFIX", "node:")

        try:
            r = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                username=redis_user,
                password=redis_pass,
                decode_responses=True
            )
            redis_key = f"{redis_prefix}{node}:ip"
            node_ip = r.get(redis_key)

            if node_ip:
                self.docker_host = f"tcp://{node_ip}:2375"
                logger.info(f"[REDIS] Node '{node}' -> IP {node_ip} → docker_host set")
            else:
                logger.warning(f"[REDIS] Node '{node}' not found in Redis — using default host")
        except Exception as e:
            logger.error(f"[REDIS] Connection error: {e}")
            logger.warning("[REMOTE] Using fallback Docker host")

        # --- Image & GPU runtime ---
        self.image = image
        self.extra_host_config = self.extra_host_config or {}

        if any(x in image for x in ["gpu", "cu", "tf", "rpl"]):
            self.extra_host_config["runtime"] = "nvidia"
            logger.info(f"[GPU] Runtime set to 'nvidia' for image '{image}'")
        else:
            self.extra_host_config.pop("runtime", None)
            logger.info(f"[CPU] Runtime set to default for image '{image}'")

        return super().start()