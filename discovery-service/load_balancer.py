import threading
import time
import logging
from typing import List, Dict, Optional
from models import Profile, NodeAllocation, UserSession, db

logger = logging.getLogger("DiscoveryAPI.LoadBalancer")

class LoadBalancer:
    def __init__(self):
        self.round_robin_counter = 0
        self.counter_lock = threading.Lock()

    def calculate_node_score(self, node: Dict) -> float:
        """
        Calculate node score based on CPU & memory usage.
        Lower score = better performance.
        """
        cpu_usage = node.get("cpu_usage_percent", 100)
        memory_usage = node.get("memory_usage_percent", 100)

        cpu_weight = 0.5
        memory_weight = 0.5

        # Calculate composite score
        score = (cpu_usage * cpu_weight) + (memory_usage * memory_weight)

        # Add penalty for overloaded nodes
        if cpu_usage > 90 or memory_usage > 90:
            score += 50  # heavy penalty
        elif cpu_usage > 80 or memory_usage > 80:
            score += 20  # medium penalty

        return round(score, 2)

    def get_next_round_robin_node(self, nodes: List[Dict]) -> Optional[Dict]:
        """
        Round Robin implementation with scoring
        """
        if not nodes:
            return None

        with self.counter_lock:
            idx = self.round_robin_counter % len(nodes)
            self.round_robin_counter = (self.round_robin_counter + 1) % 1_000_000
            return nodes[idx]

    def select_best_node(self, nodes: List[Dict]) -> Optional[Dict]:
        """
        Select node with lowest load score
        """
        if not nodes:
            return None

        for node in nodes:
            node["load_score"] = self.calculate_node_score(node)

        return min(nodes, key=lambda n: n["load_score"])

    def select_nodes_for_profile(self, nodes: List[Dict], profile: Profile) -> List[Dict]:
        """
        Select multiple nodes based on profile requirements
        """
        if not nodes or not profile:
            return []

        # Filter nodes based on profile requirements
        suitable_nodes = []
        for node in nodes:
            if self._node_meets_profile_requirements(node, profile):
                node["load_score"] = self.calculate_node_score(node)
                suitable_nodes.append(node)

        # Sort by score (best first)
        suitable_nodes.sort(key=lambda x: x["load_score"])

        # Return requested number of nodes
        return suitable_nodes[:profile.node_count]

    def _node_meets_profile_requirements(self, node: Dict, profile: Profile) -> bool:
        """
        Check if node meets profile requirements
        """
        # Check CPU and memory thresholds
        if (node.get("cpu_usage_percent", 100) >= profile.max_cpu_usage or
            node.get("memory_usage_percent", 100) >= profile.max_memory_usage):
            return False

        # Check container limit
        active_containers = (node.get("active_jupyterlab", 0) +
                           node.get("active_ray", 0))
        if active_containers >= profile.max_active_containers:
            return False

        # Check resource requirements
        if (node.get("cpu", 0) < profile.cpu_requirement or
            node.get("ram_gb", 0) < profile.memory_requirement):
            return False

        # Check GPU requirement
        if profile.gpu_required and not node.get("has_gpu", False):
            return False

        return True

    def allocate_nodes_for_session(self, session_id: str, user_id: str,
                                 profile_id: int, nodes: List[Dict]) -> List[NodeAllocation]:
        """
        Allocate nodes for a user session
        """
        profile = Profile.query.get(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        selected_nodes = self.select_nodes_for_profile(nodes, profile)
        if len(selected_nodes) < profile.node_count:
            logger.warning(f"Only {len(selected_nodes)} nodes available, "
                         f"but {profile.node_count} requested")

        # Create or update user session
        user_session = UserSession.query.filter_by(session_id=session_id).first()
        if not user_session:
            user_session = UserSession(
                session_id=session_id,
                user_id=user_id,
                profile_id=profile_id,
                requested_nodes=profile.node_count,
                allocated_nodes=len(selected_nodes),
                status='running'
            )
            db.session.add(user_session)
        else:
            user_session.allocated_nodes = len(selected_nodes)
            user_session.status = 'running'

        # Create node allocations
        allocations = []
        for node in selected_nodes:
            allocation = NodeAllocation(
                session_id=session_id,
                user_id=user_id,
                profile_id=profile_id,
                hostname=node["hostname"],
                node_ip=node["ip"],
                status='allocated'
            )
            db.session.add(allocation)
            allocations.append(allocation)

        try:
            db.session.commit()
            logger.info(f"Allocated {len(allocations)} nodes for session {session_id}")
            return allocations
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to allocate nodes: {e}")
            raise

    def deallocate_session_nodes(self, session_id: str) -> bool:
        """
        Deallocate all nodes for a session
        """
        try:
            # Update node allocations
            allocations = NodeAllocation.query.filter_by(session_id=session_id).all()
            for allocation in allocations:
                allocation.status = 'stopped'
                allocation.stopped_at = time.time()

            # Update user session
            user_session = UserSession.query.filter_by(session_id=session_id).first()
            if user_session:
                user_session.status = 'stopped'
                user_session.stopped_at = time.time()

            db.session.commit()
            logger.info(f"Deallocated nodes for session {session_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to deallocate nodes: {e}")
            return False

    def get_session_allocations(self, session_id: str) -> List[NodeAllocation]:
        """
        Get all node allocations for a session
        """
        return NodeAllocation.query.filter_by(
            session_id=session_id,
            status='allocated'
        ).all()

    def get_user_active_sessions(self, user_id: str) -> List[UserSession]:
        """
        Get all active sessions for a user
        """
        return UserSession.query.filter_by(
            user_id=user_id,
            status='running'
        ).all()

    def get_load_balancer_stats(self, nodes: List[Dict]) -> Dict:
        """
        Get load balancer statistics
        """
        if not nodes:
            return {
                "error": "No nodes available",
                "stats": None
            }

        # Calculate scores for all nodes
        for node in nodes:
            node["load_score"] = self.calculate_node_score(node)

        # Calculate statistics
        scores = [node["load_score"] for node in nodes]
        cpu_usages = [node.get("cpu_usage_percent", 0) for node in nodes]
        memory_usages = [node.get("memory_usage_percent", 0) for node in nodes]

        stats = {
            "total_nodes": len(nodes),
            "round_robin_counter": self.round_robin_counter,
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

        return stats

# Global load balancer instance
load_balancer = LoadBalancer()