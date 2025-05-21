import requests
import socket
import os
import psutil
import docker
import time

DISCOVERY_URL = os.environ.get("DISCOVERY_URL", "http://172.19.0.3:15002/register-node")

def collect_node_info():
    try:
        hostname = socket.gethostname()
        ip_address = os.popen("hostname -I").read().strip().split()[0]
        has_gpu = os.path.exists("/dev/nvidia0")
        ram_gb = round(psutil.virtual_memory().total / 1e9, 2)

        # CPU & memory usage
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        memory_usage_percent = memory.percent
        disk_usage_percent = disk.percent

        # JupyterLab container count
        docker_client = docker.from_env()
        containers = docker_client.containers.list()
        active_jupyterlab = sum(1 for c in containers if "jupyter" in c.name)

        payload = {
            "hostname": hostname,
            "ip": ip_address,
            "cpu": os.cpu_count(),
            "has_gpu": has_gpu,
            "ram_gb": ram_gb,
            "cpu_usage_percent": round(cpu_usage, 2),
            "memory_usage_percent": round(memory_usage_percent, 2),
            "disk_usage_percent": round(disk_usage_percent, 2),
            "active_jupyterlab": active_jupyterlab
        }

        return payload
    except Exception as e:
        print(f"[AGENT] Error collecting node info: {e}")
        return None

def register():
    payload = collect_node_info()
    if payload:
        try:
            resp = requests.post(DISCOVERY_URL, json=payload)
            print(f"[AGENT] Registered: {payload['hostname']} ({payload['ip']}) → {resp.status_code}")
        except Exception as e:
            print(f"[AGENT] Failed to register node: {e}")

if __name__ == "__main__":
    while True:
        register()
        time.sleep(30) # Update every seconds
