#!/usr/bin/env python3
"""Script to install Ray kernel to Jupyter"""

import os
import sys
import json
import shutil
from pathlib import Path
from jupyter_client.kernelspec import KernelSpecManager

def install_ray_kernel():
    """Install Ray kernel to Jupyter"""

    # Get the kernel spec manager
    ksm = KernelSpecManager()

    # Define kernel spec
    kernel_spec = {
        "argv": [
            sys.executable,
            "-m", "ray_kernel",
            "-f", "{connection_file}"
        ],
        "display_name": "Ray Cluster",
        "language": "python",
        "interrupt_mode": "signal",
        "env": {
            "RAY_HEAD_ADDRESS": os.environ.get("RAY_HEAD_ADDRESS", "10.21.73.122:10001"),
            "RAY_WORKER_NODES": os.environ.get("RAY_WORKER_NODES", "10.21.73.116"),
            "RAY_WORKER_IMAGE": os.environ.get("RAY_WORKER_IMAGE", "danielcrist0/ray:rpl"),
            "PYTHONPATH": "${PYTHONPATH}:/srv/jupyterhub/ray-kernel"
        },
        "metadata": {
            "description": "Ray Cluster kernel with auto-spawning workers"
        }
    }

    temp_dir = Path("/tmp/ray_kernel_spec")
    temp_dir.mkdir(exist_ok=True)

    # Write kernel.json
    kernel_json_path = temp_dir / "kernel.json"
    with open(kernel_json_path, 'w') as f:
        json.dump(kernel_spec, f, indent=2)

    # Install the kernel spec
    try:
        ksm.install_kernel_spec(str(temp_dir), kernel_name="ray_cluster", user=False, replace=True)
        print("✅ Ray kernel installed successfully!")
        print(f"📍 Kernel installed at: {ksm.get_kernel_spec('ray_cluster').resource_dir}")

        # List available kernels
        print("\n📋 Available kernels:")
        for name, spec in ksm.get_all_specs().items():
            print(f"  - {name}: {spec['spec']['display_name']}")

    except Exception as e:
        print(f"❌ Failed to install Ray kernel: {e}")
        return False

    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    return True

def uninstall_ray_kernel():
    """Uninstall Ray kernel from Jupyter"""
    ksm = KernelSpecManager()

    try:
        ksm.remove_kernel_spec("ray_cluster")
        print("✅ Ray kernel uninstalled successfully!")
    except Exception as e:
        print(f"❌ Failed to uninstall Ray kernel: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Install/Uninstall Ray kernel")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the kernel")
    args = parser.parse_args()

    if args.uninstall:
        uninstall_ray_kernel()
    else:
        install_ray_kernel()