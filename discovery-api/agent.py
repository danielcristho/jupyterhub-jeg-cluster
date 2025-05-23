import requests
import socket
import os
import psutil
import docker
import time
import gpustat

DISCOVERY_URL = os.environ.get("DISCOVERY_URL", "http://10.125.177.108:15002/register-node")

def get_gpu_stats():
    try:
        stats = gpustat.GPUStatCollection.new_query()
        gpu_info = []
        for gpu in stats.gpus:
            gpu_info.append({
                "name": gpu.name,
                "index": gpu.index,
                "uuid": gpu.uuid,
                "memory_total_mb": gpu.memory_total,
                "memory_used_mb": gpu.memory_used,
                "memory_util_percent": round(gpu.memory_used / gpu.memory_total * 100, 2) if gpu.memory_total else 0,
                "utilization_gpu_percent": gpu.utilization,
                "temperature_gpu": gpu.temperature
                # "processes": [{
                #     "pid": p.get('pid', -1),
                #     "gpu_memory_usage_mb": p.get('memory_usage', 0)
                # } for p in gpu.processes or []]
            })
        return gpu_info
    except Exception as e:
        print(f"[GPUSTAT] Failed to query GPU stat: {e}")
        return []


def collect_node_info():
    try:
        hostname = socket.gethostname()
        ip_address = os.popen("hostname -I").read().strip().split()[0]
        ram_gb = round(psutil.virtual_memory().total / 1e9, 2)

        # CPU & memory usage
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Container info
        docker_client = docker.from_env()
        containers = docker_client.containers.list()
        active_jupyterlab = sum(1 for c in containers if "jupyterrpl" in c.name)
        active_ray = sum(1 for c in containers if "ray" in c.name)

        # GPU info (single call)
        gpu_stats = get_gpu_stats()

        payload = {
            "hostname": hostname,
            "ip": ip_address,
            "cpu": os.cpu_count(),
            "gpu": gpu_stats,
            "has_gpu": len(gpu_stats) > 0,
            "ram_gb": ram_gb,
            "cpu_usage_percent": round(cpu_usage, 2),
            "memory_usage_percent": round(memory.percent, 2),
            "disk_usage_percent": round(disk.percent, 2),
            "active_jupyterlab": active_jupyterlab,
            "active_ray": active_ray
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
        time.sleep(30)
