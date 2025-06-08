import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_
from models import db, Node, NodeMetric
from services.redis_service import RedisService
from utils.scoring import calculate_node_score
from config import Config

logger = logging.getLogger(__name__)

class NodeService:
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    def register_node(self, node_data: dict) -> Tuple[bool, str]:
        """Register or update a node in both Redis and PostgreSQL"""
        hostname = node_data.get('hostname')
        if not hostname:
            return False, "Hostname is required"

        try:
            # Store in Redis for real-time data
            self.redis.set_node_info(hostname, node_data)

            # Update or create in PostgreSQL
            node = Node.query.filter_by(hostname=hostname).first()
            if not node:
                node = Node(hostname=hostname)
                db.session.add(node)

            # Update static information
            node.ip = node_data.get('ip', node.ip)
            node.cpu = node_data.get('cpu', node.cpu)
            node.ram_gb = node_data.get('ram_gb', node.ram_gb)
            node.has_gpu = node_data.get('has_gpu', node.has_gpu)
            node.gpu = node_data.get('gpu', [])
            node.is_active = True
            node.updated_at = datetime.utcnow()

            # Save metric history
            metric = NodeMetric(
                node_id=node.id if node.id else None,
                cpu_usage_percent=node_data.get('cpu_usage_percent', 0),
                memory_usage_percent=node_data.get('memory_usage_percent', 0),
                disk_usage_percent=node_data.get('disk_usage_percent', 0),
                active_jupyterlab=node_data.get('active_jupyterlab', 0),
                active_ray=node_data.get('active_ray', 0),
                total_containers=node_data.get('total_containers', 0),
                load_score=calculate_node_score(node_data)
            )

            if node.id:
                metric.node_id = node.id
                db.session.add(metric)

            db.session.commit()

            # If node is new, add metric after getting node ID
            if not metric.node_id:
                metric.node_id = node.id
                db.session.add(metric)
                db.session.commit()

            return True, "Node registered successfully"

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering node: {e}")
            return False, str(e)

    def get_all_nodes(self, include_inactive: bool = False) -> List[Dict]:
        """Get all nodes with current metrics from Redis"""
        nodes = Node.query.all()
        if not include_inactive:
            nodes = [n for n in nodes if n.is_active]

        result = []
        for node in nodes:
            # Get current metrics from Redis
            redis_data = self.redis.get_node_info(node.hostname)
            if redis_data:
                node.update_current_metrics(redis_data)
            result.append(node.to_dict())

        return result

    def get_available_nodes(self, profile_id: Optional[int] = None,
                          strict_filter: bool = False) -> List[Dict]:
        """Get available nodes based on criteria"""
        nodes = self.get_all_nodes()

        # Filter by profile if provided
        if profile_id:
            from models import Profile
            profile = Profile.query.get(profile_id)
            if profile:
                nodes = [n for n in nodes if self._node_matches_profile(n, profile)]

        # Apply usage filters
        if strict_filter:
            max_cpu = Config.STRICT_MAX_CPU_USAGE
            max_memory = Config.STRICT_MAX_MEMORY_USAGE
            max_containers = Config.STRICT_MAX_CONTAINERS
        else:
            max_cpu = Config.DEFAULT_MAX_CPU_USAGE
            max_memory = Config.DEFAULT_MAX_MEMORY_USAGE
            max_containers = None

        filtered = []
        for node in nodes:
            if node.get('cpu_usage_percent', 100) >= max_cpu:
                continue
            if node.get('memory_usage_percent', 100) >= max_memory:
                continue
            if max_containers and node.get('total_containers', 0) >= max_containers:
                continue

            # Add load score
            node['load_score'] = calculate_node_score(node)
            filtered.append(node)

        # Sort by load score
        filtered.sort(key=lambda x: x['load_score'])
        return filtered

    def select_nodes_for_profile(self, profile_id: int,
                               num_nodes: Optional[int] = None,
                               user_id: Optional[str] = None) -> List[Dict]:
        """Select best nodes for a given profile"""
        from models import Profile, NodeSelection

        profile = Profile.query.get(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        # Determine number of nodes to select
        if num_nodes is None:
            num_nodes = profile.min_nodes
        else:
            num_nodes = max(profile.min_nodes, min(num_nodes, profile.max_nodes))

        # Get available nodes matching profile
        available = self.get_available_nodes(profile_id=profile_id)

        if len(available) < num_nodes:
            raise ValueError(f"Not enough nodes available. Required: {num_nodes}, Available: {len(available)}")

        # Select best nodes
        selected = available[:num_nodes]

        # Record selection
        selection = NodeSelection(
            profile_id=profile_id,
            user_id=user_id,
            selected_nodes=[{'id': n.get('id'), 'hostname': n.get('hostname')} for n in selected],
            selection_reason='profile_based'
        )
        db.session.add(selection)
        db.session.commit()

        return selected

    def get_node_by_hostname(self, hostname: str) -> Optional[Dict]:
        """Get specific node by hostname"""
        node = Node.query.filter_by(hostname=hostname).first()
        if not node:
            return None

        # Get current metrics from Redis
        redis_data = self.redis.get_node_info(hostname)
        if redis_data:
            node.update_current_metrics(redis_data)

        return node.to_dict()

    def get_node_metrics_history(self, hostname: str, hours: int = 24) -> List[Dict]:
        """Get historical metrics for a node"""
        node = Node.query.filter_by(hostname=hostname).first()
        if not node:
            return []

        since = datetime.utcnow() - timedelta(hours=hours)
        metrics = NodeMetric.query.filter(
            and_(
                NodeMetric.node_id == node.id,
                NodeMetric.recorded_at >= since
            )
        ).order_by(NodeMetric.recorded_at.desc()).all()

        return [m.to_dict() for m in metrics]

    def mark_nodes_inactive(self):
        """Mark nodes as inactive if not updated recently"""
        # This could be run periodically to mark stale nodes
        threshold = datetime.utcnow() - timedelta(seconds=Config.REDIS_EXPIRE_SECONDS * 2)
        Node.query.filter(
            and_(
                Node.updated_at < threshold,
                Node.is_active == True
            )
        ).update({'is_active': False})
        db.session.commit()

    def _node_matches_profile(self, node_dict: dict, profile) -> bool:
        """Check if node matches profile requirements"""
        if profile.cpu_requirement and node_dict.get('cpu', 0) < profile.cpu_requirement:
            return False
        if profile.ram_requirement and node_dict.get('ram_gb', 0) < profile.ram_requirement:
            return False
        if profile.gpu_required and not node_dict.get('has_gpu', False):
            return False
        if node_dict.get('cpu_usage_percent', 100) > profile.max_cpu_usage:
            return False
        if node_dict.get('memory_usage_percent', 100) > profile.max_memory_usage:
            return False
        return True