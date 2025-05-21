from flask import Flask, jsonify, request
from flask_cors import CORS
import redis
import time, os, requests, json
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app, origins="*")
load_dotenv()

"""Redis Configuration"""
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "redis@pass")
REDIS_EXPIRE_SECONDS = int(os.environ.get("REDIS_EXPIRE_SECONDS", 3600))

try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
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

@app.route("/register-node", methods=["POST"])
def register_node():
    data = request.get_json()
    hostname = data.get("hostname")
    if not hostname:
        return jsonify({"error": "hostname is required"}), 400

    key = f"node:{hostname}:info"
    redis_client.set(key, json.dumps(data))
    redis_client.expire(key, REDIS_EXPIRE_SECONDS)

    return jsonify({"status": "ok"}), 200

@app.route("/all-nodes")
def all_nodes():
    return jsonify(_load_nodes(filtered=False))

@app.route("/available-nodes")
def available_nodes():
    return jsonify(_load_nodes(filtered=True))

@app.route("/balanced-node")
def balanced_node():
    try:
        nodes = _load_nodes(filtered=True)
        selected = min(nodes, key=lambda n: n.get("memory_usage_percentage", 100))
        return jsonify(selected)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _load_nodes(filtered=True):
    keys = redis_client.keys("node:*:info")
    result = []

    for key in keys:
        raw = redis_client.get(key)
        if not raw:
            continue
        data = json.loads(raw)
        result.append({
            "hostname": data.get("hostname"),
            "ip": data.get("ip"),
            "cpu": data.get("cpu", 0),
            "ram_gb": data.get("ram_gb", 0),
            "has_gpu": data.get("has_gpu", False),
            "cpu_usage_percent": data.get("cpu_usage_percent", 100),
            "memory_usage_percent": data.get("memory_usage_percent", 100),
            "disk_usage_percent": data.get("disk_usage_percent", 100),
            "active_jupyterlab": data.get("active_jupyterlab", 0),
            "is_in_use_by_jupyterhub": data.get("active_jupyterlab", 0) > 0,
        })

    if filtered:
        result = [
            node for node in result
            if node["cpu_usage_percent"] < 80 and node["memory_usage_percent"] < 85
        ]

    return result

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=15002)