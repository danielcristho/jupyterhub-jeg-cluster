from flask import Blueprint, jsonify, request
from services.node_service import NodeService
from services.redis_service import RedisService
from utils.load_balancer import get_round_robin_counter, select_nodes_by_algorithm
import logging

logger = logging.getLogger(__name__)

# Create blueprint
node_bp = Blueprint('nodes', __name__)

# Initialize services
redis_service = RedisService()
node_service = NodeService(redis_service)

@node_bp.route("/register-node", methods=["POST"])
def register_node():
    """Register or update a node"""
    data = request.get_json()
    success, message = node_service.register_node(data)

    if success:
        return jsonify({"status": "ok", "message": message}), 200
    else:
        return jsonify({"error": message}), 400

@node_bp.route("/all-nodes")
def all_nodes():
    """Get all registered nodes"""
    nodes = node_service.get_all_nodes(include_inactive=True)
    return jsonify({
        "total_nodes": len(nodes),
        "nodes": nodes
    })

@node_bp.route("/available-nodes")
def available_nodes():
    """Get available nodes with load balancing info"""
    try:
        # Get filter parameters
        profile_id = request.args.get('profile_id', type=int)
        algorithm = request.args.get('algorithm', 'round_robin')
        count = request.args.get('count', 1, type=int)

        # Get available nodes
        nodes = node_service.get_available_nodes(profile_id=profile_id)

        # Select nodes based on algorithm
        selected = select_nodes_by_algorithm(nodes, algorithm, count)

        return jsonify({
            "total_available_nodes": len(nodes),
            "selected_nodes": selected,
            "all_available_nodes": nodes,
            "load_balancing": {
                "algorithm": algorithm,
                "round_robin_counter": get_round_robin_counter(),
                "requested_count": count,
                "selected_count": len(selected)
            }
        })
    except Exception as e:
        logger.error(f"Error in available_nodes: {e}")
        return jsonify({"error": str(e)}), 500

@node_bp.route("/node/<hostname>")
def get_node_by_hostname(hostname):
    """Get specific node by hostname"""
    node = node_service.get_node_by_hostname(hostname)
    if node:
        return jsonify(node)
    else:
        return jsonify({"error": f"Node '{hostname}' not found"}), 404

@node_bp.route("/node/<hostname>/metrics")
def get_node_metrics(hostname):
    """Get historical metrics for a node"""
    hours = request.args.get('hours', 24, type=int)
    metrics = node_service.get_node_metrics_history(hostname, hours)

    return jsonify({
        "hostname": hostname,
        "hours": hours,
        "metrics_count": len(metrics),
        "metrics": metrics
    })

@node_bp.route("/select-nodes", methods=["POST"])
def select_nodes():
    """Select nodes based on requirements"""
    data = request.get_json()

    try:
        # Get parameters
        profile_id = data.get('profile_id')
        num_nodes = data.get('num_nodes', 1)
        user_id = data.get('user_id')

        if not profile_id:
            return jsonify({"error": "profile_id is required"}), 400

        # Select nodes
        selected = node_service.select_nodes_for_profile(
            profile_id=profile_id,
            num_nodes=num_nodes,
            user_id=user_id
        )

        return jsonify({
            "status": "ok",
            "selected_nodes": selected,
            "count": len(selected)
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error selecting nodes: {e}")
        return jsonify({"error": "Internal error"}), 500

@node_bp.route("/cluster-summary")
def cluster_summary():
    """Get cluster summary statistics"""
    nodes = node_service.get_all_nodes()

    total_containers = {
        "jupyterlab": sum(n.get("active_jupyterlab", 0) for n in nodes),
        "ray": sum(n.get("active_ray", 0) for n in nodes),
        "total": sum(n.get("total_containers", 0) for n in nodes),
    }

    resource_usage = {
        "avg_cpu": round(sum(n.get("cpu_usage_percent", 0) for n in nodes) / len(nodes), 2) if nodes else 0,
        "avg_memory": round(sum(n.get("memory_usage_percent", 0) for n in nodes) / len(nodes), 2) if nodes else 0,
    }

    return jsonify({
        "total_nodes": len(nodes),
        "active_nodes": len([n for n in nodes if n.get("is_active")]),
        "total_containers": total_containers,
        "resource_usage": resource_usage
    })