from dockerspawner import DockerSpawner
from traitlets import Unicode, Dict
import redis, os, logging, asyncio
from dotenv import load_dotenv

load_dotenv()

class MultiNodeSpawner(DockerSpawner):
    host = Unicode("tcp://127.0.0.1:2375", config=True)
    tls_config = Dict({}, config=True)

    node = Unicode("", config=True)
    image = Unicode("", config=True)

    async def start(self):
        logger = logging.getLogger("jupyterhub")
        logger.info(f"[SPAWNER] user_options: {self.user_options}")

        node = self.user_options.get("node", "")
        node_ip = self.user_options.get("node_ip", "")
        image = self.user_options.get("image", "danielcristh0/jupyterlab:cpu")

        # CRITICAL: Fail fast if no remote configuration
        if not node or not node_ip:
            logger.error(f"[SPAWNER] CRITICAL: Missing remote node config. Node: {node}, IP: {node_ip}")
            raise ValueError("Remote node configuration missing. Cannot spawn to local machine.")

        self.host = f"tcp://{node_ip}:2375"
        self.tls_config = {}
        logger.info(f"[SPAWNER] Docker host FORCED to: {self.host}")

        if 'tcp://127.0.0.1' in self.host or 'localhost' in self.host:
            logger.error(f"[SPAWNER] CRITICAL: Host is still local: {self.host}")
            raise ValueError("Failed to configure remote Docker host")

        # Redis discovery config
        redis_host = os.environ.get("REDIS_HOST", "redis")
        redis_port = int(os.environ.get("REDIS_PORT", 6379))
        redis_pass = os.environ.get("REDIS_PASSWORD", "redis@pass")
        redis_prefix = os.environ.get("REDIS_DISCOVERY_KEY_PREFIX", "node:")

        if not node_ip and node:
            try:
                r = redis.StrictRedis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_pass,
                    decode_responses=True
                )
                redis_key = f"{redis_prefix}{node}:ip"
                node_ip_from_redis = r.get(redis_key)
                logger.info(f"[SPAWNER] Redis fallback - key: {redis_key} → {node_ip_from_redis}")

                if node_ip_from_redis:
                    self.host = f"tcp://{node_ip_from_redis}:2375"
                    self.tls_config = {}
                    logger.info(f"[SPAWNER] Redis fallback - Docker host set to {self.host}")
                else:
                    logger.error("[SPAWNER] CRITICAL: No node IP found in Redis and none provided in options")
                    raise ValueError("Cannot determine remote node IP address")
            except Exception as e:
                logger.error(f"[SPAWNER] Redis error and no node_ip in options: {e}")
                raise ValueError(f"Failed to get remote node configuration: {e}")

        # Image & runtime configuration
        self.image = image
        self.extra_host_config = self.extra_host_config or {}

        # Configure GPU runtime if needed
        if any(x in image for x in ["gpu", "cu", "tf", "rpl"]):
            self.extra_host_config["runtime"] = "nvidia"
            logger.info(f"[SPAWNER] GPU runtime enabled for {image}")
        else:
            self.extra_host_config.pop("runtime", None)
            logger.info(f"[SPAWNER] CPU image used: {image}")

        # Configure environment variables for JupyterLab
        self.environment = self.environment or {}
        self.environment.update({
            'JUPYTER_ENABLE_LAB': 'yes',
            'RESTARTABLE': 'yes',
            'JUPYTER_TOKEN': '',  # Disable token authentication
            'JUPYTER_ALLOW_INSECURE_WRITES': 'true',
            'JUPYTER_PORT': '8888',
            'JUPYTER_IP': '0.0.0.0'  # Bind to all interfaces
        })

        self.extra_host_config["port_bindings"] = {
            "8888/tcp": ("0.0.0.0", None)
        }

        self.extra_host_config.pop("network_mode", None)
        self.use_internal_ip = False

        logger.info(f"[SPAWNER] Starting container with image: {self.image}")
        logger.info(f"[SPAWNER] Docker host: {self.host}")
        logger.info(f"[SPAWNER] Environment: {self.environment}")
        logger.info(f"[SPAWNER] Extra host config: {self.extra_host_config}")

        # Final validation before starting
        if 'tcp://127.0.0.1' in self.host:
            logger.error(f"[SPAWNER] FINAL CHECK FAILED: Still using local host: {self.host}")
            raise ValueError("Remote host configuration failed - would spawn locally")

        try:
            # Call parent start method
            result = await super().start()

            await asyncio.sleep(3)

            # Verify container is running
            container = self.client.inspect_container(self.container_id)
            if container["State"]["Status"] != "running":
                logger.error(f"[SPAWNER] Container not running: {container['State']['Status']}")
                raise Exception(f"Container failed to start: {container['State']['Status']}")

            # Get the actual port mapping
            ports = container["NetworkSettings"]["Ports"]
            if "8888/tcp" in ports and ports["8888/tcp"]:
                host_port = ports["8888/tcp"][0]["HostPort"]
                node_ip_final = self.host.replace("tcp://", "").split(":")[0]

                self.ip = node_ip_final
                self.port = int(host_port)

                logger.info(f"[SPAWNER] Container started successfully on REMOTE host")
                logger.info(f"[SPAWNER] Remote node IP: {node_ip_final}")
                logger.info(f"[SPAWNER] Access URL: http://{self.ip}:{self.port}")

                # Final validation - ensure we're not somehow local
                if self.ip in ['127.0.0.1', 'localhost'] or self.ip.startswith('192.168.'):
                    logger.warning(f"[SPAWNER] WARNING: IP looks local: {self.ip}")
                    # Don't fail here, but log warning

            else:
                logger.error("[SPAWNER] Port 8888 not properly exposed")
                raise Exception("Container port 8888 not properly exposed")

            return result

        except Exception as e:
            logger.error(f"[SPAWNER] Failed to start container: {e}")
            # Clean up if there's an error
            if hasattr(self, 'container_id') and self.container_id:
                try:
                    self.client.stop_container(self.container_id)
                    self.client.remove_container(self.container_id)
                except:
                    pass
            raise