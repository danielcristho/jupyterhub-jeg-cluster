#!/usr/bin/env python3
"""
Kernel Debug Information Script
Provides comprehensive information about the kernel execution environment
"""

import os
import socket
import psutil
import json
from datetime import datetime
import sys

def get_kernel_info():
    """Get comprehensive kernel and system information"""
    info = {
        'timestamp': datetime.now().isoformat(),
        'system': {
            'hostname': socket.gethostname(),
            'container_ip': socket.gethostbyname(socket.gethostname()),
            'cpu_count': psutil.cpu_count(),
            'memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'disk_usage_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
            'python_version': sys.version.split()[0]
        },
        'environment': {
            'kernel_node_hostname': os.environ.get('KERNEL_NODE_HOSTNAME', 'unknown'),
            'kernel_node_ip': os.environ.get('KERNEL_NODE_IP', 'unknown'),
            'user': os.environ.get('USER', 'unknown'),
            'home': os.environ.get('HOME', 'unknown'),
            'pythonpath': os.environ.get('PYTHONPATH', 'not_set')
        },
        'jupyter': {
            'kernel_id': os.environ.get('KERNEL_ID', 'unknown'),
            'kernel_spec': 'python3'
        }
    }
    return info

def display_kernel_info():
    """Display kernel information in a nice format"""
    info = get_kernel_info()
    
    print("=" * 60)
    print("🔬 KERNEL EXECUTION ENVIRONMENT INFO")
    print("=" * 60)
    
    print(f"📅 Timestamp: {info['timestamp']}")
    print(f"🖥️  Hostname: {info['system']['hostname']}")
    print(f"🌐 Container IP: {info['system']['container_ip']}")
    print(f"🏷️  Node Hostname: {info['environment']['kernel_node_hostname']}")
    print(f"📍 Node IP: {info['environment']['kernel_node_ip']}")
    print(f"⚙️  CPU Cores: {info['system']['cpu_count']}")
    print(f"💾 Memory: {info['system']['memory_gb']} GB")
    print(f"💽 Disk: {info['system']['disk_usage_gb']} GB")
    print(f"🐍 Python: {info['system']['python_version']}")
    print(f"👤 User: {info['environment']['user']}")
    
    print("\n" + "=" * 60)
    
    return info

def show_node_info():
    """Simplified version for quick node identification"""
    print("\n🏷️  Current Execution Node:")
    print(f"   Hostname: {os.environ.get('KERNEL_NODE_HOSTNAME', socket.gethostname())}")
    print(f"   IP: {os.environ.get('KERNEL_NODE_IP', 'unknown')}")
    print(f"   Container: {socket.gethostname()}")

def kernel_startup_message():
    """Display startup message when kernel initializes"""
    print("✅ Kernel initialized successfully!")
    print("📝 Available debug functions:")
    print("   - display_kernel_info(): Show complete system information")
    print("   - show_node_info(): Show current node information")
    print("   - get_kernel_info(): Get info as JSON dict")
    show_node_info()

# Auto-run startup message when imported
if __name__ == "__main__":
    # If run directly, show full info
    display_kernel_info()
else:
    # If imported, show startup message
    try:
        kernel_startup_message()
    except Exception as e:
        print(f"Error in kernel startup: {e}")

# Make functions available when imported
__all__ = ['get_kernel_info', 'display_kernel_info', 'show_node_info', 'kernel_startup_message']