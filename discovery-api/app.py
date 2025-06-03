from flask import Flask, jsonify, request
from flask_cors import CORS
from redis import ConnectionPool, Redis
from dotenv import load_dotenv
import threading
import time
import os
import json
import logging

# Flask app init
app = Flask(__name__)
CORS(app, origins="*")

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DiscoveryAPI")

# Redis Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "redis@pass")
REDIS_EXPIRE_SECONDS = int(os.environ.get("REDIS_EXPIRE_SECONDS", 45))

print(f"[DEBUG] Connecting to Redis: {REDIS_HOST}:{REDIS_PORT}")

# Round robin counter
round_robin_counter = 0
counter_lock = threading.Lock()

# Connect to Redis
try:
    pool = ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client = Redis(connection_pool=pool)
    redis_client.ping()
    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    redis_client = None
    logger.error(f"Failed to connect to Redis: {e}")

# ===================== Utility Functions ===================== #

def calculate_node_score(node):
    """
    Hitung score dari node dari cpu & memory usage.
    Skor lebih rendah = performa lebih baik.
    """
    cpu_usage = node.get("cpu_usage_percent", 100)
    memory_usage = node.get("memory_usage_percent", 100)

    cpu_weight = 0.5
    memory_weight = 0.5

    # Hitung composite score
    score = (cpu_usage * cpu_weight) + (memory_usage * memory_weight)

    # penalty jika node sudah overload
    if cpu_usage > 90 or memory_usage > 90:
        score += 50  # heavy penalty
    elif cpu_usage > 80 or memory_usage > 80:
        score += 20  # medium penalty

    return round(score, 2)

def get_next_round_robin_node(nodes):
    """
    Implementasi Round Robin dengan scoring
    """
    global round_robin_counter
    if not nodes:
        return None
    with counter_lock:
        idx = round_robin_counter % len(nodes)
        round_robin_counter = (round_robin_counter + 1) % 1_000_000
        return nodes[idx]

def _load_nodes(filtered=True, strict_filter=False):
    """
    Memuat data node dari Redis.
    Jika `filtered=True`, hanya node yang sehat (usage rendah) akan dimasukkan.
    Jika `strict_filter=True`, filter ketat digunakan untuk keperluan JupyterHub.
    """
    if not redis_client:
        logger.error("Redis unavailable in _load_nodes")
        return []

    try:
        result = []
        for key in redis_client.keys("node:*:info"):
            ttl = redis_client.ttl(key)
            if ttl <= 0:
                continue
            try:
                data = json.loads(redis_client.get(key))
                node = {
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
                result.append(node)
            except Exception as e:
                logger.warning(f"Failed to parse {key}: {e}")

        if filtered:
            if strict_filter:
                result = [n for n in result if n["cpu_usage_percent"] < 60 and n["memory_usage_percent"] < 60 and (n["active_jupyterlab"] + n["active_ray"]) < 5]
            else:
                result = [n for n in result if n["cpu_usage_percent"] < 80 and n["memory_usage_percent"] < 85]

        return result
    except Exception as e:
        logger.error(f"Error in _load_nodes: {e}")
        return []

# ===================== Routes ===================== #

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
    """Menerima data regitrasi node (hostname, IP, usage) dan menyimpannya ke Redis."""
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    data = request.get_json()
    hostname, ip = data.get("hostname"), data.get("ip")
    if not hostname:
        return jsonify({"error": "hostname is required"}), 400

    try:
        redis_client.set(f"node:{hostname}:info", json.dumps(data), ex=REDIS_EXPIRE_SECONDS)
        redis_client.set(f"node:{hostname}:ip", ip, ex=REDIS_EXPIRE_SECONDS)
        return jsonify({"status": "ok", "stored": True})
    except Exception as e:
        logger.error(f"Redis store error: {e}")
        return jsonify({"error": f"Redis error: {str(e)}"}), 500


@app.route("/all-nodes")
def all_nodes():
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500
    return jsonify(_load_nodes(filtered=False))


@app.route("/available-nodes")
def available_nodes():
    """Mengembalikan node yang tersedia menggunakan load balancing berbasis round-robin"""
    try:
        nodes = _load_nodes(filtered=True)
        for node in nodes:
            node["load_score"] = calculate_node_score(node)
        nodes.sort(key=lambda n: n["load_score"])
        selected_node = get_next_round_robin_node(nodes)
        return jsonify({
            "total_available_nodes": len(nodes),
            "selected_node": selected_node,
            "all_available_nodes": nodes,
            "load_balancing": {
                "algorithm": "round_robin_with_scoring",
                "round_robin_counter": round_robin_counter
            }
        })
    except Exception as e:
        logger.error(f"Error in /available-nodes: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/jupyterhub-nodes")
def jupyterhub_nodes():
    """
    Endpoint khusus untuk JupyterHub dengan filter yang lebih ketat
    """
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = _load_nodes(filtered=True, strict_filter=True)

        if not nodes:
            return jsonify({
                "error": "No suitable nodes for JupyterHub",
                "criteria": "CPU < 60%, Memory < 60%, Active Containers < 5",
                "total_nodes": 0,
                "selected_node": None,
                "load_balancing": {
                    "algorithm": "round_robin_with_scoring",
                    "round_robin_counter": round_robin_counter
                }
            }), 404

        # Hitung score untuk setiap node
        for node in nodes:
            node["load_score"] = calculate_node_score(node)

        # Sort nodes berdasarkan score (ascending - score terendah di depan)
        nodes_sorted_by_score = sorted(nodes, key=lambda x: x["load_score"])

        print(f"[DEBUG] Sorted nodes by score:")
        for i, node in enumerate(nodes_sorted_by_score):
            print(f"[DEBUG] {i}: {node['hostname']} - Score: {node['load_score']}")

        # Pilih node menggunakan round robin dari nodes yang sudah di-sort
        selected_node = get_next_round_robin_node(nodes_sorted_by_score)

        print(f"[DEBUG] Selected node: {selected_node['hostname']} with score: {selected_node['load_score']}")

        # Tambahkan informasi load balancing
        response = {
            "total_available_nodes": len(nodes),
            "selected_node": selected_node,
            "load_balancing": {
                "algorithm": "round_robin_with_scoring",
                "round_robin_counter": round_robin_counter,
                "selection_timestamp": int(time.time()),
                "filter_applied": "jupyterhub_strict (CPU<60%, Memory<60%, Containers<5)"
            },
            "all_available_nodes": nodes_sorted_by_score,
            "selection_criteria": {
                "max_cpu_usage": 60,
                "max_memory_usage": 60,
                "max_active_containers": 5,
                "note": "Stricter criteria for JupyterHub workloads"
            },
            "score_explanation": {
                "calculation": "CPU_usage * 0.5 + Memory_usage * 0.5",
                "penalties": {
                    "heavy_load": "CPU > 90% OR Memory > 90% (+50 points)",
                    "medium_load": "CPU > 80% OR Memory > 80% (+20 points)"
                },
                "note": "Lower score = better performance"
            }
        }

        return jsonify(response)

    except Exception as e:
        print(f"[ERROR] Error in jupyterhub_nodes: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/balanced-node")
def balanced_node():
    """
    Endpoint untuk mendapatkan node dengan load terendah (pure load balancing)
    """
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = _load_nodes(filtered=True)
        if not nodes:
            return jsonify({"error": "No available nodes"}), 404

        # Hitung score dan pilih yang terbaik
        for node in nodes:
            node["load_score"] = calculate_node_score(node)

        selected = min(nodes, key=lambda n: n["load_score"])

        return jsonify({
            "selected_node": selected,
            "selection_method": "lowest_load_score",
            "total_available": len(nodes)
        })

    except Exception as e:
        print(f"[ERROR] Error in balanced_node: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/load-balancer-stats")
def load_balancer_stats():
    """
    Endpoint untuk melihat statistik load balancer
    """
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = _load_nodes(filtered=True)

        if not nodes:
            return jsonify({
                "error": "No nodes available",
                "stats": None
            }), 404

        # Hitung score untuk semua nodes
        for node in nodes:
            node["load_score"] = calculate_node_score(node)

        # Statistik
        scores = [node["load_score"] for node in nodes]
        cpu_usages = [node.get("cpu_usage_percent", 0) for node in nodes]
        memory_usages = [node.get("memory_usage_percent", 0) for node in nodes]

        stats = {
            "total_nodes": len(nodes),
            "round_robin_counter": round_robin_counter,
            "load_scores": {
                "min": min(scores),
                "max": max(scores),
                "avg": round(sum(scores) / len(scores), 2)
            },
            "cpu_usage": {
                "min": min(cpu_usages),
                "max": max(cpu_usages),
                "avg": round(sum(cpu_usages) / len(cpu_usages), 2)
            },
            "memory_usage": {
                "min": min(memory_usages),
                "max": max(memory_usages),
                "avg": round(sum(memory_usages) / len(memory_usages), 2)
            },
            "nodes_detail": sorted(nodes, key=lambda x: x["load_score"])
        }

        return jsonify(stats)

    except Exception as e:
        print(f"[ERROR] Error in load_balancer_stats: {e}")
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


@app.route("/cluster-summary")
def cluster_cluster():
    """Get cluster summary of containers and resources too"""
    if not redis_client:
        return jsonify({"error": "Redis not available"}), 500

    nodes = _load_nodes(filtered=False)

    summary = {
        "total_nodes": len(nodes),
        "total_containers": {
            "jupyterlab": sum(node.get("active_jupyterlab", 0) for node in nodes),
            "ray": sum(node.get("active_ray", 0) for node in nodes),
            "total": sum(node.get("total_containers", 0) for node in nodes),
        },
        "resource_usage": {
            "avg_cpu": round(sum(node.get("cpu_usage_percent", 0) for node in nodes) / len(nodes), 2) if nodes else 0,
            "avg_memory": round(sum(node.get("memory_usage_percent", 0) for node in nodes) / len(nodes), 2) if nodes else 0,
        }
    }

    return jsonify(summary)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=15002)