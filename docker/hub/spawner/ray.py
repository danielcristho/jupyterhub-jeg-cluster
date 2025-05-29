"""
RayWorkerSpawner

Utility to launch a Ray worker container on the same node as JupyterLab.
"""

import docker
import logging

class RayWorkerSpawner: