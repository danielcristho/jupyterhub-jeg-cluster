"""
Ray initialization script for JupyterLab singleuser servers
This script runs automatically when IPython kernel starts
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ray_init')

# Add ray-kernel to Python path
ray_kernel_path = '/home/jovyan/ray-kernel'
if ray_kernel_path not in sys.path:
    sys.path.insert(0, ray_kernel_path)

def setup_ray_environment():
    """Setup Ray environment variables"""
    try:
        # Set default Ray environment variables if not already set
        os.environ.setdefault('RAY_HEAD_ADDRESS', '10.21.73.122:10001')
        os.environ.setdefault('RAY_WORKER_NODES', '10.21.73.116')
        os.environ.setdefault('RAY_WORKER_IMAGE', 'danielcrist0/ray:rpl')

        # Set JupyterHub user environment
        os.environ.setdefault('JUPYTERHUB_USER', os.environ.get('USER', 'jovyan'))

        logger.info(f"Ray environment configured:")
        logger.info(f"  RAY_HEAD_ADDRESS: {os.environ.get('RAY_HEAD_ADDRESS')}")
        logger.info(f"  RAY_WORKER_NODES: {os.environ.get('RAY_WORKER_NODES')}")
        logger.info(f"  RAY_WORKER_IMAGE: {os.environ.get('RAY_WORKER_IMAGE')}")

    except Exception as e:
        logger.error(f"Failed to setup Ray environment: {e}")

def load_ray_magic():
    """Load Ray magic commands"""
    try:
        # Create Ray magic commands for regular IPython kernels
        from IPython import get_ipython

        ipython = get_ipython()
        if ipython is not None:
            # Define Ray magic commands
            def ray_status_magic(line):
                """Show Ray cluster status"""
                try:
                    import ray
                    if ray.is_initialized():
                        print(f"Ray Status:")
                        print(f"  Cluster nodes: {len(ray.nodes())}")
                        print(f"  Available resources: {ray.available_resources()}")
                        print(f"  Dashboard URL: http://{ray.get_dashboard_url()}")
                    else:
                        print("Ray is not initialized. Use ray.init() to connect.")
                except ImportError:
                    print("Ray is not installed.")
                except Exception as e:
                    print(f"Error getting Ray status: {e}")

            def ray_connect_magic(line):
                """Connect to Ray cluster"""
                try:
                    import ray
                    ray_address = os.environ.get('RAY_HEAD_ADDRESS', '127.0.0.1:10001')
                    ray.init(address=ray_address, ignore_reinit_error=True)
                    print(f"Connected to Ray cluster at {ray_address}")
                    print(f"Available resources: {ray.available_resources()}")
                except ImportError:
                    print("Ray is not installed.")
                except Exception as e:
                    print(f"Error connecting to Ray: {e}")

            def ray_help_magic(line):
                """Show Ray magic commands help"""
                help_text = """
Available Ray magic commands:
  %ray_status    - Show Ray cluster status
  %ray_connect   - Connect to Ray cluster
  %ray_help      - Show this help message

To use Ray in your notebook:
  import ray
  ray.init(address='{}')
""".format(os.environ.get('RAY_HEAD_ADDRESS', '127.0.0.1:10001'))
                print(help_text)

            # Register magic commands
            ipython.register_magic_function(ray_status_magic, 'line', 'ray_status')
            ipython.register_magic_function(ray_connect_magic, 'line', 'ray_connect')
            ipython.register_magic_function(ray_help_magic, 'line', 'ray_help')

            logger.info("Ray magic commands loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load Ray magic commands: {e}")

def check_ray_kernel_available():
    """Check if Ray kernel is properly installed"""
    try:
        from jupyter_client.kernelspec import KernelSpecManager
        ksm = KernelSpecManager()
        kernels = ksm.get_all_specs()

        if 'ray_cluster' in kernels:
            logger.info("✅ Ray Cluster kernel is available")
            return True
        else:
            logger.warning("❌ Ray Cluster kernel not found")
            return False

    except Exception as e:
        logger.error(f"Error checking Ray kernel: {e}")
        return False

# Initialize Ray environment
setup_ray_environment()
load_ray_magic()
check_ray_kernel_available()

# Print welcome message
print("🚀 Ray integration loaded!")
print("📋 Available magic commands: %ray_status, %ray_connect, %ray_help")
print("🔧 Ray Cluster kernel should be available in the kernel selector")
print("")