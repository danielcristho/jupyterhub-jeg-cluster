import requests
import socket
import os
import psutil
import docker
import time
import gpustat
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DISCOVERY_URL = os.environ.get("DISCOVERY_URL", "http://127.0.0.1:15002/register-node")

def register():
    print("[DEBUG] adding node...")
    payload = collect_node_info()
    if payload:
        print(f"[DEBUG] Send Info: {payload}")
        try:
            resp = requests.post(DISCOVERY_URL, json=payload)
            print(f"[AGENT] Registered: {payload['hostname']} ({payload['ip']}) → {resp.status_code}")
            
            if resp.status_code != 200:
                try:
                    error_detail = resp.json()
                    print(f"[ERROR] Response: {error_detail}")
                except:
                    print(f"[ERROR] Raw response: {resp.text}")
                    
        except Exception as e:
            print(f"[AGENT] Failed to register node: {e}")
    else:
        print("[DEBUG] Payload tidak boleh kosong!!")

def collect_node_info():
    """Collect node or server info"""
    try:
        hostname = socket.gethostname()
        ip_address = os.popen("hostname -I").read().strip().split()[0]
        ram_gb = round(psutil.virtual_memory().total / 1e9, 2)

        # CPU & memory usage
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Container info
        container_info = get_container_info()

        # GPU info (single call)
        gpu_stats = get_gpu_stats()

        payload = {
            "hostname": hostname,
            "ip": ip_address,
            "cpu_cores": os.cpu_count(),                   
            "gpu_info": gpu_stats,                         
            "has_gpu": len(gpu_stats) > 0,
            "ram_gb": ram_gb,
            "max_containers": 10,                          
            "is_active": True,                            
            
            "cpu_usage_percent": round(cpu_usage, 2),
            "memory_usage_percent": round(memory.percent, 2),
            "disk_usage_percent": round(disk.percent, 2),
            "active_jupyterlab": container_info["jupyterlab_count"],
            "active_ray": container_info["ray_count"],
            "total_containers": container_info["total_count"],
            "last_updated": datetime.now().isoformat() + "Z"
        }

        return payload
    except Exception as e:
        print(f"[AGENT] Error collecting node info: {e}")
        return None

def get_gpu_stats():
    """Get GPU Details"""
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
            })
        return gpu_info
    except Exception as e:
        print(f"[GPUSTAT] NVIDIA GPU not available or error: {e}")
        return []

def detect_amd_gpu():
    """Try to get AMD GPU details"""
    try:
        output = os.popen("lspci | grep VGA").read()
        if "AMD" in output:
            return [{
                "name": "AMD GPU",
                "index": 0,
                "uuid": "N/A",
                "memory_total_mb": None,
                "memory_used_mb": None,
                "memory_util_percent": None,
                "utilization_gpu_percent": None,
                "temperature_gpu": None
            }]
    except Exception as e:
        print(f"[AMD DETECTION] Failed: {e}")
    return []

def get_container_info():
    """Get container details, count jupyter and ray container"""
    container_info = {
        "jupyterlab_count": 0,
        "ray_count": 0,
        "total_count": 0,
        "details": []
    }

    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list()
        container_info["total_count"] = len(containers)
        """Count Jupyterlab&Ray Containers"""
        for container in containers:
            container_name = container.name.lower()
            container_image = container.image.tags[0] if container.image.tags else "unknown"

            if any(keyword in container_name for keyword in ["jupyter"]) or \
                any(keyword in container_image.lower() for keyword in ["jupyter"]):
                    container_info["jupyterlab_count"] += 1
            if any(keyword in container_name for keyword in ["ray"]) or \
                any(keyword in container_image.lower() for keyword in ["ray"]):
                    container_info["ray_count"] += 1

        print(f"[DEBUG] Container Summary: Total={container_info['total_count']}, "
                f"JupyterLab={container_info['jupyterlab_count']}, Ray={container_info['ray_count']}")

    except Exception as e:
        print(f"[DOCKER] Error getting container info: {e}")

    return container_info


if __name__ == "__main__":
    print(f"[AGENT] Starting node registration agent...")
    print(f"[AGENT] Target URL: {DISCOVERY_URL}")
    
    while True:
        register()
        time.sleep(15)