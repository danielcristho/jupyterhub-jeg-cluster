from flask import Flask, jsonify, request
from flask_cors import CORS
import redis
import os, json
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app, origins="*")
load_dotenv()

"""Redis Configuration"""
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "redis@pass")
REDIS_EXPIRE_SECONDS = int(os.environ.get("REDIS_EXPIRE_SECONDS", 3600))

print(f"[DEBUG] Connecting to Redis: {REDIS_HOST}:{REDIS_PORT}")

try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client.ping()
    print(f"[DEBUG] Redis connection successful!")
except Exception as e:
    redis_client = None
    print(f"[ERROR] Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT} → {e}")


@app.route("/health-check")
def health_check():
    redis_status = "connected" if redis_client else "disconnected"
    return jsonify({
        "status": "ok",
        "message": "Hello, from [DiscoveryAPI]",
        "redis_status": redis_status,
        "redis_host": REDIS_HOST,
        "redis_port": REDIS_PORT
    }), 200

@app.route("/register-node", methods=["POST"])
def register_node():
    if not redis_client:
        print("[ERROR] Redis client not available")
        return jsonify({"error": "Redis not available"}), 500

    data = request.get_json()
    hostname = data.get("hostname")
    ip = data.get("ip")

    print(f"[DEBUG] Received registration request: {data}")
    print(f"[DEBUG] Redis client connected to: {REDIS_HOST}:{REDIS_PORT}")

    if not hostname:
        return jsonify({"error": "hostname is required"}), 400

    try:
        # Set node info
        info_key = f"node:{hostname}:info"
        ip_key = f"node:{hostname}:ip"

        redis_client.set(info_key, json.dumps(data), ex=REDIS_EXPIRE_SECONDS)
        redis_client.set(ip_key, ip, ex=REDIS_EXPIRE_SECONDS)

        print(f"[DEBUG] Set Redis key {info_key}")
        print(f"[DEBUG] Set Redis key {ip_key} = {ip}")

        # Verify data was stored
        stored_info = redis_client.get(info_key)
        stored_ip = redis_client.get(ip_key)
        print(f"[DEBUG] Verification - stored info: {stored_info}")
        print(f"[DEBUG] Verification - stored ip: {stored_ip}")

        return jsonify({"status": "ok", "stored": True}), 200

    except Exception as e:
        print(f"[ERROR] Failed to store in Redis: {e}")
        return jsonify({"error": f"Redis error: {str(e)}"}), 500


@app.route("/all-nodes")
def all_nodes():
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500
    return jsonify(_load_nodes(filtered=False))

@app.route("/available-nodes")
def available_nodes():
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500
    return jsonify(_load_nodes(filtered=True))

@app.route("/balanced-node")
def balanced_node():
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = _load_nodes(filtered=True)
        if not nodes:
            return jsonify({"error": "No available nodes"}), 404

        selected = min(nodes, key=lambda n: n.get("memory_usage_percentage", 100))
        return jsonify(selected)
    except Exception as e:
        print(f"[ERROR] Error in balanced_node: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/debug-redis")
def debug_redis():
    """Debug endpoint to check Redis status"""
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    try:
        # Get all keys
        all_keys = redis_client.keys("*")
        node_keys = redis_client.keys("node:*")
        info_keys = redis_client.keys("node:*:info")
        ip_keys = redis_client.keys("node:*:ip")

        debug_info = {
            "redis_connected": True,
            "total_keys": len(all_keys),
            "all_keys": all_keys,
            "node_keys": node_keys,
            "info_keys": info_keys,
            "ip_keys": ip_keys
        }

        # Get all node data
        node_data = {}
        for key in info_keys:
            data = redis_client.get(key)
            ttl = redis_client.ttl(key)
            node_data[key] = {
                "data": data,
                "ttl": ttl,
                "parsed": json.loads(data) if data else None
            }

        debug_info["node_data"] = node_data

        # Get IP data
        ip_data = {}
        for key in ip_keys:
            ip = redis_client.get(key)
            ttl = redis_client.ttl(key)
            ip_data[key] = {
                "ip": ip,
                "ttl": ttl
            }

        debug_info["ip_data"] = ip_data

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({"error": f"Redis debug error: {str(e)}"}), 500

@app.route("/node/<hostname>")
def get_node_by_hostname(hostname):
    """Get specific node by hostname - for JupyterHub compatibility"""
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    try:
        info_key = f"node:{hostname}:info"
        ip_key = f"node:{hostname}:ip"

        info_data = redis_client.get(info_key)
        ip_data = redis_client.get(ip_key)

        if not info_data:
            return jsonify({"error": f"Node '{hostname}' not found"}), 404

        node_info = json.loads(info_data)

        return jsonify({
            "hostname": hostname,
            "ip": ip_data or node_info.get("ip"),
            "info": node_info,
            "found": True
        })

    except Exception as e:
        return jsonify({"error": f"Error retrieving node: {str(e)}"}), 500

def _load_nodes(filtered=True):
    if not redis_client:
        print("[ERROR] Redis client not available in _load_nodes")
        return []

    try:
        keys = redis_client.keys("node:*:info")
        print(f"[DEBUG] Found {len(keys)} node info keys: {keys}")
        result = []

        for key in keys:
            ttl = redis_client.ttl(key)
            if ttl is None or ttl <= 0:
                print(f"[DEBUG] Skipping expired node: {key} (ttl={ttl})")
                continue

            raw = redis_client.get(key)
            if not raw:
                print(f"[DEBUG] No data for key: {key}")
                continue

            try:
                data = json.loads(raw)
                node_info = {
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
                    "is_in_use_by_jupyterhub": data.get("active_jupyterlab", 0) > 0,
                    "last_updated": data.get("last_updated")
                }
                result.append(node_info)
                print(f"[DEBUG] Loaded node: {node_info['hostname']}")
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON decode error for key {key}: {e}")

        if filtered:
            original_count = len(result)
            result = [
                node for node in result
                if node["cpu_usage_percent"] < 80 and node["memory_usage_percent"] < 85
            ]
            print(f"[DEBUG] Filtered nodes: {original_count} -> {len(result)}")

        return result

    except Exception as e:
        print(f"[ERROR] Error in _load_nodes: {e}")
        return []

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=15002)