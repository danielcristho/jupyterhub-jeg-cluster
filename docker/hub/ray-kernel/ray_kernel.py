"""Simple Ray cluster kernel"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from ipykernel.ipkernel import IPythonKernel
from ipykernel.kernelapp import IPKernelApp
from worker_manager import RayWorkerManager

load_dotenv()

class RayClusterKernel(IPythonKernel):
    """Ray kernel to spawn ray worker"""

    implementation = 'Ray Cluster'
    implementation_version = '1.0.0'
    language = 'python'
    banner = "Ray Kernel - Sharing Resources"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_manager = None
        self.user_name = os.environ.get('JUPYTERHUB_USER', 'jupyter')
        self.ray_head_address = os.environ.get('RAY_HEAD_ADDRESS', '127.0.0.1:10001')
        self.worker_nodes = os.environ.get('RAY_WORKER_NODES', '').split(',')
        self.worker_nodes = [node.strip() for node in self.worker_nodes if node.strip()]

        # Config logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('ray_kernel')

    def start(self):
        """Start jupyter kernel and ray worker"""
        super().start()

        # Welcome message
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': f"Ray Cluster Kernel Started...\n"
                    f"Ray Head: {self.ray_head_address}\n"
                    f"Worker Nodes: {', '.join(self.worker_nodes) if self.worker_nodes else 'None'}\n\n"
        })

        if self.worker_nodes:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._spawn_ray_workers())
            else:
                loop.run_until_complete(self._spawn_ray_workers())
        else:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': "No Ray worker nodes configured. Set RAY_WORKER_NODES environment variable.\n"
            })

    async def _spawn_ray_workers(self):
        """Spawn Ray worker container"""
        try:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': f"Spawning Ray worker on {len(self.worker_nodes)} nodes...\n"
            })

            self.worker_manager = RayWorkerManager(
                ray_head_address=self.ray_head_address,
                worker_nodes=self.worker_nodes,
                logger=self.logger  # Fixed typo: was 'loggeer'
            )

            # spawn workers
            workers = await self.worker_manager.spawn_workers(self.user_name)

            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': f"Successfully spawned {len(workers)} Ray workers!\n\n"
            })

            self._initialize_ray()

        except Exception as e:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f"Failed to spawn Ray workers: {e}\n"
            })

    def _initialize_ray(self):
        """Initialize Ray in jupyter kernel"""
        init_code = f"""
import ray

try:
    ray.init(address='{self.ray_head_address}', ignore_reinit_error=True)
    print("Connected to Ray cluster!")
    print(f"Available resources: {{ray.available_resources()}}")
    print(f"Cluster nodes: {{len(ray.nodes())}}")
    print(f"Ready for distributed computing!")

    def ray_status():
        return {{
            'nodes': len(ray.nodes()),
            'resources': ray.available_resources()
        }}

    globals()['ray_status'] = ray_status

except Exception as e:
    print(f"Failed to connect to Ray: {{e}}")
"""
        # Execute in kernel
        self.shell.run_cell(init_code, silent=False)

    async def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        """Handle Ray commands"""

        if code.strip().startswith('%ray'):
            return await self._handle_ray_magic(code.strip())

        return await super().do_execute(code, silent, store_history, user_expressions, allow_stdin)

    async def _handle_ray_magic(self, code):
        """Handle Ray magic commands"""
        try:
            if code == '%ray_status':
                if self.worker_manager:
                    status = self.worker_manager.get_worker_status()
                    self.send_response(self.iopub_socket, 'stream', {
                        'name': 'stdout',
                        'text': f"Ray Workers ({len(status)} total):\n" +
                                "\n".join([f"  Worker {w['worker_id']} on {w['node_ip']}: {w.get('status', 'unknown')}" for w in status]) + "\n"
                    })
                else:
                    self.send_response(self.iopub_socket, 'stream', {
                        'name': 'stdout',
                        'text': "No worker manager initialized\n"
                    })

            elif code == '%ray_restart':
                if self.worker_manager:
                    self.send_response(self.iopub_socket, 'stream', {
                        'name': 'stdout',
                        'text': "Restarting Ray workers...\n"
                    })
                    await self.worker_manager.stop_workers(self.user_name)
                    await asyncio.sleep(2)
                    workers = await self.worker_manager.spawn_workers(self.user_name)
                    self.send_response(self.iopub_socket, 'stream', {
                        'name': 'stdout',
                        'text': f"Restarted {len(workers)} Ray workers\n"
                    })
                else:
                    self.send_response(self.iopub_socket, 'stream', {
                        'name': 'stdout',
                        'text': "No worker manager initialized\n"
                    })

            elif code == '%ray_help':
                help_text = """
Available Ray magic commands:
  %ray_status    - Show current Ray workers status
  %ray_restart   - Restart all Ray workers
  %ray_help      - Show this help message
  %ray_connect   - Reconnect to Ray cluster
  %ray_info      - Show Ray cluster information
"""
                self.send_response(self.iopub_socket, 'stream', {
                    'name': 'stdout',
                    'text': help_text
                })

            elif code == '%ray_connect':
                self._initialize_ray()

            elif code == '%ray_info':
                info_code = """
import ray
if ray.is_initialized():
    print(f"Ray Dashboard: http://{ray.get_dashboard_url()}")
    print(f"Ray Version: {ray.__version__}")
    print(f"Available Resources: {ray.available_resources()}")
    print(f"Total Nodes: {len(ray.nodes())}")
else:
    print("Ray is not initialized. Use %ray_connect to connect.")
"""
                self.shell.run_cell(info_code, silent=False)

            return {'status': 'ok', 'execution_count': self.execution_count}

        except Exception as e:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f"Ray magic error: {e}\n"
            })
            return {'status': 'error', 'execution_count': self.execution_count}

    async def do_shutdown(self, restart):
        """Cleanup when shutting down"""
        if self.worker_manager:
            try:
                await self.worker_manager.stop_workers(self.user_name)
                self.logger.info("Ray workers stopped successfully")
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")

        await super().do_shutdown(restart)

class RayClusterKernelApp(IPKernelApp):
    kernel_class = RayClusterKernel

if __name__ == '__main__':
    RayClusterKernelApp.launch_instance()