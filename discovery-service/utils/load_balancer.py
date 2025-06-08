import threading
from typing import List, Dict, Optional
from utils.scoring import calculate_node_score

# Global round-robin counter
_round_robin_counter = 0
_counter_lock = threading.Lock()

def get_round_robin_counter() -> int:
    """Get current round-robin counter value"""
    global _round_robin_counter
    return _round_robin_counter

def get_next_round_robin_node(nodes: List[Dict]) -> Optional[Dict]:
    """
    Select next node using round-robin algorithm.
    Assumes nodes are already sorted by score/preference.
    """
    global _round_robin_counter

    if not nodes:
        return None

    with _counter_lock:
        idx = _round_robin_counter % len(nodes)
        _round_robin_counter = (_round_robin_counter + 1) % 1_000_000
        return nodes[idx]

def select_best_nodes(nodes: List[Dict], count: int = 1) -> List[Dict]:
    """
    Select the best N nodes based on load score.
    """
    if not nodes or count <= 0:
        return []

    # Calculate scores for all nodes
    for node in nodes:
        if 'load_score' not in node:
            node['load_score'] = calculate_node_score(node)

    # Sort by score (lower is better)
    sorted_nodes = sorted(nodes, key=lambda x: x['load_score'])

    # Return top N nodes
    return sorted_nodes[:min(count, len(sorted_nodes))]

def select_nodes_by_algorithm(nodes: List[Dict],
                            algorithm: str = 'round_robin',
                            count: int = 1) -> List[Dict]:
    """
    Select nodes using specified algorithm.

    Algorithms:
    - 'round_robin': Round-robin selection from sorted nodes
    - 'best_fit': Select nodes with lowest load scores
    - 'random': Random selection (useful for testing)
    """
    if not nodes:
        return []

    # Add scores to all nodes
    for node in nodes:
        if 'load_score' not in node:
            node['load_score'] = calculate_node_score(node)

    if algorithm == 'best_fit':
        return select_best_nodes(nodes, count)

    elif algorithm == 'round_robin':
        # Sort by score first
        sorted_nodes = sorted(nodes, key=lambda x: x['load_score'])
        selected = []
        for _ in range(min(count, len(sorted_nodes))):
            node = get_next_round_robin_node(sorted_nodes)
            if node and node not in selected:
                selected.append(node)
        return selected

    elif algorithm == 'random':
        import random
        available = nodes.copy()
        random.shuffle(available)
        return available[:min(count, len(available))]

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

def distribute_load(nodes: List[Dict],
                   workload_size: int,
                   max_per_node: int = 1) -> Dict[str, int]:
    """
    Distribute workload across nodes.
    Returns mapping of hostname to number of units assigned.
    """
    if not nodes or workload_size <= 0:
        return {}

    distribution = {}
    remaining = workload_size
    node_index = 0

    # Sort nodes by score
    sorted_nodes = sorted(nodes, key=lambda x: x.get('load_score', 100))

    while remaining > 0 and node_index < len(sorted_nodes):
        node = sorted_nodes[node_index]
        hostname = node.get('hostname')

        if hostname not in distribution:
            distribution[hostname] = 0

        # Assign up to max_per_node units to this node
        units = min(remaining, max_per_node - distribution[hostname])
        if units > 0:
            distribution[hostname] += units
            remaining -= units

        # Move to next node if current is at capacity
        if distribution[hostname] >= max_per_node:
            node_index += 1
        else:
            # Round-robin to next node for distribution
            node_index = (node_index + 1) % len(sorted_nodes)

    return distribution