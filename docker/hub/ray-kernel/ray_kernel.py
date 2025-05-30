""""Simple Ray cluster kernel"""

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
    implementation_version = '1.0.0.'
    language = 'python'
    banner = "Ray Kernel - Sharing Resources"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_manager = None
        self.user_name = os.environ.get('JUPYTERHUB', 'jupyter')
        self.ray_head_address = os.environ.get('RAY_HEAD_ADDRESS', '127.0.0.1:10001')
        self.ray_head_address = os.environ.get('RAY_HEAD_ADDRESS', '127.0.0.1:10001')
        self.worker_nodes = os.environ.get('RAY_WORKER_NODES', '').split(',')
        self.worker_nodes = [nodes.strip() for node in self.worker_nodes if node.strip()]

        # Config logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('ray_kernel')

    def start(self):
        """Start jupyter kernel and ray worker"""
        super().start()

        # Welcome message
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': f"Ray Cluster Kernel Startted...\n"
                    f"Ray Head: {self.ray_head_address}\n"
                    f"Worker Nodes: {', '.join(self.worker_nodes) if self.worker_nodes else 'None'}\n\n"
        })

        # Initilize Ray worker
        if self.worker_nodes:
            asyncio.create_task(self._spawn_ray_workers())
        else:
            self.send_response(self.iopub_socket, 'stream',{
                'name': 'stdout',
                'text': "No Ray worker nodes configured. Set RAY_WORKER_NODES environment variable.\n"
            })

    async def spawn_ray_workers(self):
        "Spawn Ray worker container"
        try:
            self.send_response(self.iopub_socket, 'stream',{
                'name': 'stdout',
                'text': f"Spawning Ray worker on {len(self.worker_nodes)} nodes...\n"
            })

            # Initilize workers manager
            self.worker_manager = RayWorkerManager(
                ray_head_address=self.ray_head_address,
                worker_nodes=self.worker_nodes,
                loggeer=self.logger
            )

            # spawn workers
            workers = await self.worker_manager.spawn_workers(self.user_name)

            self.send_response(self.iopub_socket, 'stream',{
                'name': 'stdout',
                'text': f"Successfully spawned {len(workers)} Ray workers!\n\n"
            })

            self._initialize_ray()

        except Exception as e:
            self.send_response(self.iopub_socket, 'stream',{
                'name': 'stderr',
                'text': f"Failed to spawn Ray workers: {e}\n"
            })

    def _initilize_ray(self):
        """Initilize Ray in jupy kernel"""
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
        self.shell.run_cell(init_code, silent=True)

    async def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        """Handle Ray commands"""

        if code.strip().startswith('%ray'):
            return await self._handle_ray_magic(code.strip())

        return await super().do_execute(code, silent, store_history, user_expressions, allow_stdin)

    async def _handle_ray_magic(self, code):
        """Handle Ray commands"""
        try:
            if code == '%ray_status' and self.worker_manager:
                status = self.worker_manager.get_worker_status()
                self.send_response(self.iopub_socket, 'stream', {
                    'name': 'stdout',
                    'text': f"Ray Workers ({len(status)} total):\n" +
                            "\n".join([f"  Worker {w['worker_id']} on {w['node_ip']}: {w.get('status', 'unknown')}" for w in status]) + "\n"
                })

            elif code == '%ray_restart' and self.worker_manager:
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

            return {'status': 'ok', 'execution_count': self.execution_count}

        except Exception as e:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f"Ray magic error: {e}\n"
            })
            return {'status': 'error', 'execution_count': self.execution_count}

    async def shutdown_kernel(self, restart):
        """Cleanup when shutting down"""
        if self.worker_manager:
            try:
                await self.worker_manager.stop_workers(self.user_name)
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")

        await super().shutdown_kernel(restart)

class RayClusterKernelApp(IPKernelApp):
    kernel_class = RayClusterKernel

if __name__ == '__main__':
    RayClusterKernelApp.launch_instance()
