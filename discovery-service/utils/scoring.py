from config import Config

def calculate_node_score(node_data: dict) -> float:
    """
    Calculate score for a node based on CPU and memory usage.
    Lower score = better performance.
    """
    cpu_usage = node_data.get("cpu_usage_percent", 100)
    memory_usage = node_data.get("memory_usage_percent", 100)

    # Weighted score calculation
    score = (cpu_usage * Config.CPU_WEIGHT) + (memory_usage * Config.MEMORY_WEIGHT)

    # Apply penalties for overloaded nodes
    if cpu_usage > 90 or memory_usage > 90:
        score += Config.HEAVY_PENALTY  # Heavy penalty for overloaded nodes
    elif cpu_usage > 80 or memory_usage > 80:
        score += Config.MEDIUM_PENALTY  # Medium penalty for heavily used nodes

    return round(score, 2)