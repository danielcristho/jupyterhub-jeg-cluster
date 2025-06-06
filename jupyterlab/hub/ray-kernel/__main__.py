"""Main entry point for Ray kernel"""

from .ray_kernel import RayClusterKernelApp

if __name__ == '__main__':
    RayClusterKernelApp.launch_instance()