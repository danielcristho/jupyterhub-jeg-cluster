import os
import ray
import socket

RAY_ADDRESS = os.getenv("RAY_ADDRESS", "ray://10.21.73.122:10001")

def log(msg):
    print(f"[Ray Autoconnect] {msg}")

try:
    if not ray.is_initialized():
        ray.init(address=RAY_ADDRESS, namespace="default")
        cluster_resources = ray.cluster_resources()
        hostname = socket.gethostname()
        log(f"Connected to Ray cluster at {RAY_ADDRESS}")
        log(f"Node: {hostname}")
        log(f"Cluster Resources: {cluster_resources}")
        log(f"Ray Dashboard assumed at {RAY_ADDRESS.split('//')[1].split(':')[0]}:8265")
    else:
        log("Ray already initialized.")
except Exception as e:
    log(f"❌ Failed to connect: {e}")