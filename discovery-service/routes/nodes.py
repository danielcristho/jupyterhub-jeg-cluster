from flask import Blueprint, request, jsonify
from redis_utils import redis_manager
from load_balancer import load_balancer
import logging
import time

logger = logging.getLogger("DiscoveryAPI.Nodes")

nodes_bp = Blueprint('nodes', __name__)

@nodes_bp.route("/register-node", methods=["POST"])
def register_node():
    """Register node information in Redis"""
    if not redis_manager.is_connected():
        return jsonify({"error": "Redis not available"}), 500

    data = request.get_json()
    hostname = data.get("hostname")

    if not hostname:
        return jsonify({"error": "hostname is required"}), 400

    try:
        success = redis_manager.store_node_info(hostname, data)
        if success:
            logger.info(f"Node registered: {hostname}")
            return jsonify({"status": "ok", "stored": True})
        else:
            return jsonify({"error": "Failed to store node info"}), 500
    except Exception as e:
        logger.error(f"Redis store error: {e}")
        return jsonify({"error": f"Redis error: {str(e)}"}), 500

@nodes_bp.route("/all-nodes")
def all_nodes():
    """Get all nodes (unfiltered)"""
    if not redis_manager.is_connected():
        return jsonify({"error": "Redis not available"}), 500

    nodes = redis_manager.get_all_nodes(filtered=False)
    return jsonify({
        "nodes": nodes,
        "total_nodes": len(nodes),
        "timestamp": int(time.time())
    })

@nodes_bp.route("/available-nodes")
def available_nodes():
    """Get available nodes with load balancing"""
    try:
        if not redis_manager.is_connected():
            return jsonify({"error": "Redis not available"}), 500

        nodes = redis_manager.get_all_nodes(filtered=True)
        if not nodes:
            return jsonify({"error": "No available nodes"}), 404

        # Calculate scores and sort
        for node in nodes:
            node["load_score"] = load_balancer.calculate_node_score(node)

        nodes.sort(key=lambda n: n["load_score"])
        selected_node = load_balancer.get_next_round_robin_node(nodes)

        return jsonify({
            "total_available_nodes": len(nodes),
            "selected_node": selected_node,
            "all_available_nodes": nodes,
            "load_balancing": {
                "algorithm": "round_robin_with_scoring",
                "round_robin_counter": load_balancer.round_robin_counter,
                "timestamp": int(time.time())
            }
        })
    except Exception as e:
        logger.error(f"Error in /available-nodes: {e}")
        return jsonify({"error": str(e)}), 500

@nodes_bp.route("/jupyterhub-nodes")
def jupyterhub_nodes():
    """
    Legacy endpoint for JupyterHub compatibility (single node selection)
    Recommend using /api/allocate-nodes for new implementations
    """
    if not redis_manager.is_connected():
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = redis_manager.get_all_nodes(filtered=True, strict_filter=True)

        if not nodes:
            return jsonify({
                "error": "No suitable nodes for JupyterHub",
                "criteria": "CPU < 60%, Memory < 60%, Active Containers < 5",
                "total_nodes": 0,
                "selected_node": None,
                "recommendation": "Use /api/allocate-nodes with profile-based allocation"
            }), 404

        # Calculate scores and select best node
        for node in nodes:
            node["load_score"] = load_balancer.calculate_node_score(node)

        nodes.sort(key=lambda x: x["load_score"])
        selected_node = load_balancer.get_next_round_robin_node(nodes)

        return jsonify({
            "total_available_nodes": len(nodes),
            "selected_node": selected_node,
            "load_balancing": {
                "algorithm": "round_robin_with_scoring",
                "round_robin_counter": load_balancer.round_robin_counter,
                "selection_timestamp": int(time.time()),
                "filter_applied": "jupyterhub_strict (CPU<60%, Memory<60%, Containers<5)"
            },
            "all_available_nodes": nodes,
            "selection_criteria": {
                "max_cpu_usage": 60,
                "max_memory_usage": 60,
                "max_active_containers": 5,
                "note": "Stricter criteria for JupyterHub workloads"
            },
            "recommendation": {
                "message": "Consider using profile-based allocation",
                "new_endpoint": "/api/allocate-nodes",
                "benefits": "Multi-node support, better resource management, session tracking"
            }
        })

    except Exception as e:
        logger.error(f"Error in jupyterhub_nodes: {e}")
        return jsonify({"error": str(e)}), 500

@nodes_bp.route("/balanced-node")
def balanced_node():
    """Get node with lowest load score"""
    if not redis_manager.is_connected():
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = redis_manager.get_all_nodes(filtered=True)
        if not nodes:
            return jsonify({"error": "No available nodes"}), 404

        selected = load_balancer.select_best_node(nodes)

        return jsonify({
            "selected_node": selected,
            "selection_method": "lowest_load_score",
            "total_available": len(nodes),
            "timestamp": int(time.time())
        })

    except Exception as e:
        logger.error(f"Error in balanced_node: {e}")
        return jsonify({"error": str(e)}), 500

@nodes_bp.route("/node/<hostname>")
def get_node_by_hostname(hostname):
    """Get specific node by hostname"""
    if not redis_manager.is_connected():
        return jsonify({"error": "Redis not available"}), 500

    try:
        node_info = redis_manager.get_node_info(hostname)

        if not node_info:
            return jsonify({"error": f"Node '{hostname}' not found"}), 404

        return jsonify({
            "hostname": hostname,
            "info": node_info,
            "found": True,
            "timestamp": int(time.time())
        })

    except Exception as e:
        return jsonify({"error": f"Error retrieving node: {str(e)}"}), 500

@nodes_bp.route("/cluster-summary")
def cluster_summary():
    """Get cluster summary"""
    if not redis_manager.is_connected():
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = redis_manager.get_all_nodes(filtered=False)

        if not nodes:
            return jsonify({
                "total_nodes": 0,
                "message": "No nodes registered"
            })

        summary = {
            "total_nodes": len(nodes),
            "total_containers": {
                "jupyterlab": sum(node.get("active_jupyterlab", 0) for node in nodes),
                "ray": sum(node.get("active_ray", 0) for node in nodes),
                "total": sum(node.get("total_containers", 0) for node in nodes),
            },
            "resource_usage": {
                "avg_cpu": round(sum(node.get("cpu_usage_percent", 0) for node in nodes) / len(nodes), 2),
                "avg_memory": round(sum(node.get("memory_usage_percent", 0) for node in nodes) / len(nodes), 2),
                "avg_disk": round(sum(node.get("disk_usage_percent", 0) for node in nodes) / len(nodes), 2),
            },
            "node_health": {
                "healthy": len([n for n in nodes if n.get("cpu_usage_percent", 100) < 80 and n.get("memory_usage_percent", 100) < 85]),
                "overloaded": len([n for n in nodes if n.get("cpu_usage_percent", 100) >= 90 or n.get("memory_usage_percent", 100) >= 90]),
                "warning": len([n for n in nodes if 80 <= n.get("cpu_usage_percent", 100) < 90 or 85 <= n.get("memory_usage_percent", 100) < 90])
            },
            "gpu_summary": {
                "total_gpu_nodes": len([n for n in nodes if n.get("has_gpu", False)]),
                "total_gpus": sum(len(node.get("gpu", [])) for node in nodes)
            },
            "timestamp": int(time.time())
        }

        return jsonify(summary)

    except Exception as e:
        logger.error(f"Error in cluster_summary: {e}")
        return jsonify({"error": str(e)}), 500

@nodes_bp.route("/load-balancer-stats")
def load_balancer_stats():
    """Get load balancer statistics"""
    if not redis_manager.is_connected():
        return jsonify({"error": "Redis not available"}), 500

    try:
        nodes = redis_manager.get_all_nodes(filtered=True)
        stats = load_balancer.get_load_balancer_stats(nodes)
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error in load_balancer_stats: {e}")
        return jsonify({"error": str(e)}), 500

@nodes_bp.route("/debug-redis")
def debug_redis():
    """Debug endpoint to check Redis status"""
    debug_info = redis_manager.get_debug_info()
    return jsonify(debug_info)