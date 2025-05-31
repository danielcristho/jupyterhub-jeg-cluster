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
        except Exception as e:
            print(f"[AGENT] Failed to register node: {e}")
    else:
        print("[DEBUG] Payload kosong, tidak dikirim.")

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
            "cpu": os.cpu_count(),
            "gpu": gpu_stats,
            "has_gpu": len(gpu_stats) > 0,
            "ram_gb": ram_gb,
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
                # "processes": [{
                #     "pid": p.get('pid', -1),
                #     "gpu_memory_usage_mb": p.get('memory_usage', 0)
                # } for p in gpu.processes or []]
            })
        return gpu_info
    except Exception as e:
        # print(f"[GPUSTAT] Failed to query GPU stat: {e}")
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