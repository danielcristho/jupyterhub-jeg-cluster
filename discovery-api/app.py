from flask import Flask, jsonify, request
import redis
import time, os, requests
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

"""Redis Configuration"""
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_USER = os.environ.get("REDIS_USER", "redis")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "redis@pass")
REDIS_EXPIRE_SECONDS = int(os.environ.get("REDIS_EXPIRE_SECONDS", 3600))

"""Ray Dashboard API"""
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8265")

try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        username=REDIS_USER,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client.ping()
except Exception as e:
    redis_client = None
    print(f"[DiscoveryAPI] Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT} → {e}")


@app.route("/health-check")
def health_check():
    return jsonify({"status": "ok", "message": "Hello, from [DiscoveryAPI]"}), 200

@app.route("/all-nodes")
def all_nodes():
    return _get_nodes(filtered=False)

@app.route("/available-nodes")
def available_nodes():
    return _get_nodes(filtered=True)

@app.route("/jupyter-activity", methods=["POST"])
def track_jupyter_activity():
    data = request.get_json()
    node = data.get("node", "unknown")
    user = data.get("user", "unknown")
    timestamp = data.get("timestamp", "unknown")

    if not redis_client:
        return jsonify({"error": "[DiscoveryAPI] Redis not connected"}), 500

    try:
        key = f"node:{node}:jupyter_users"
        value = f"{user}|{timestamp}"
        """rpush, inserts all the specified values at the tail of the list stored at the key."""
        redis_client.rpush(key, value)
        redis_client.expire(key, REDIS_EXPIRE_SECONDS)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_jupyter_users_for_node(node_name):
    if not redis_client:
        return []

    try:
        key = f"node:{node_name}: jupyter_users"
        users = redis_client.lrange(key, 0, -1)
        parsed = [
            {"user": u.split("|")[0], "timestamp": u.split("|")[1]}
            for u in users if "|" in u
        ]
        return parsed
    except Exception:
        return []


def _get_nodes(filtered=True):
    SUMMARY_ENDPOINT = "/nodes?view=summary"

    try:
        resp = requests.get(f"{DASHBOARD_URL}{SUMMARY_ENDPOINT}", timeout=20)
        resp.raise_for_status()
        summary = resp.json()["data"]["summary"]

        result = []
        for node in summary:
            raylet = node.get("raylet", {})
            start_time_ms = 0
            now = time.time()
            uptime_minutes = None


            try:
                start_time_ms = float(raylet.get("startTimeMs", 0))
                now = float(node.get("now", time.time()))
                uptime_minutes = round((now - (start_time_ms / 1000)) / 60, 2)
            except (ValueError, TypeError):
                uptime_minutes = None

            """Get resources total"""
            resources = raylet.get("resourcesTotal", {})
            try:
                cpu = float(resources.get("CPU", 0))
            except (ValueError, TypeError):
                cpu = 0.0
            try:
                mem = float(resources.get("memory", 0))
                memory_total_gb = round(mem / 1e9, 2)
            except (ValueError, TypeError):
                memory_total_gb = 0.0
            try:
                obj_mem = float(resources.get("object_store_memory", 0))
                object_store_memory_gb = round(obj_mem / 1e9, 2)
            except (ValueError, TypeError):
                object_store_memory_gb = 0.0
            try:
                gpu_list = node.get("gpus", [])
                gpu_total = len(gpu_list)
                has_gpu = gpu_total > 0
            except Exception:
                gpu_total = 0
                has_gpu = False

            # CPU usage
            try:
                cpu_usage_percent = float(node.get("cpu", 0))
            except (ValueError, TypeError):
                cpu_usage_percent = 0.0

            # Memory usage
            mem_info = node.get("mem", [0, 0, 0, 0])
            try:
                memory_total_bytes = float(mem_info[0])
                memory_used_bytes = float(mem_info[0]) - float(mem_info[1])
                memory_usage_percent = float(mem_info[2])
                memory_used_gb = round(memory_used_bytes / 1e9, 2)
            except (ValueError, TypeError, IndexError):
                memory_total_bytes = 0
                memory_used_bytes = 0
                memory_usage_percent = 0
                memory_used_gb = 0

            # Object store memory usage
            try:
                object_store_used_memory = float(raylet.get("objectStoreUsedMemory", 0))
                object_store_avail_memory = float(raylet.get("objectStoreAvailableMemory", 0))
                if object_store_avail_memory > 0:
                    object_store_usage_percent = (object_store_used_memory /
                                                (object_store_used_memory + object_store_avail_memory)) * 100
                else:
                    object_store_usage_percent = 0
                object_store_used_gb = round(object_store_used_memory / 1e9, 2)
            except (ValueError, TypeError):
                object_store_used_memory = 0
                object_store_usage_percent = 0
                object_store_used_gb = 0

            # Network stats
            try:
                network_sent_bytes = float(node.get("network", [0, 0])[0])
                network_received_bytes = float(node.get("network", [0, 0])[1])
                network_sent_mb = round(network_sent_bytes / 1e6, 2)
                network_received_mb = round(network_received_bytes / 1e6, 2)
            except (ValueError, TypeError, IndexError):
                network_sent_bytes = 0
                network_received_bytes = 0
                network_sent_mb = 0
                network_received_mb = 0

            """Node state and load"""
            state = node.get("status", "UNKNOWN")
            load_avg = node.get("loadAvg", [[0, 0, 0], [0, 0, 0]])
            load_1min = load_avg[0][0] if isinstance(load_avg, list) and len(load_avg) > 0 else 0

            # Workers info
            workers_stats = raylet.get("coreWorkersStats", [])
            worker_count = len(workers_stats)
            hostname = node.get("hostname", "unknown")
            active_users = get_jupyter_users_for_node(hostname)

            result.append({
                "node_id": raylet.get("nodeId", "unknown"),
                "ip": node.get("ip", "unknown"),
                "hostname": node.get("hostname", "unknown"),
                "is_head": raylet.get("isHeadNode", False),
                "state": state,
                "start_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_ms / 1000)) if start_time_ms else None,
                "uptime_minutes": uptime_minutes,

                # CPU stats
                "cpu_total": cpu,
                "cpu_usage_percent": cpu_usage_percent,
                "load_1min": load_1min,

                # Memory stats
                "memory_total_gb": memory_total_gb,
                "memory_used_gb": memory_used_gb,
                "memory_usage_percent": memory_usage_percent,

                # Object store stats
                "object_store_memory_gb": object_store_memory_gb,
                "object_store_used_gb": object_store_used_gb,
                "object_store_usage_percent": round(object_store_usage_percent, 2),

                # GPU stats
                "gpu_total": gpu_total,
                "has_gpu": has_gpu,

                # Network stats
                "network_sent_mb": network_sent_mb,
                "network_received_mb": network_received_mb,

                # Workers stats
                "worker_count": worker_count,

                # Jupyterhub activity info
                "active_users": active_users,
                "is_in_use_by_jupyterhub": len(active_users) > 0,

            })
            redis_client.set(f"node:{hostname}:ip", node.get("ip", ""))
            redis_client.expire(f"node:{hostname}:ip", REDIS_EXPIRE_SECONDS)

        if filtered:
            valid_states = {"ALIVE", "IDLE", "RUNNING"}
            result = [node for node in result if node["state"] in valid_states]

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=15002)