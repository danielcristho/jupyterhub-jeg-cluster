"""Integrates server option form and images validation"""

import os
from spawner.multinode import MultiNodeSpawner

def configure_spawner(c):
    c.JupyterHub.spawner_class = MultiNodeSpawner
    c.Spawner.options_form = open("form/form.html").read()

    allowed_images = {
        "danielcristh0/jupyterlab:cpu": "danielcristh0/jupyterlab:cpu",
        "danielcristh0/jupyterlab:gpu": "danielcristh0/jupyterlab:gpu",
    }
    c.DockerSpawner.allowed_images = allowed_images

    def options_from_form(formdata):
        raw_image = formdata.get("image", ["danielcristh0/jupyterlab:cpu"])[0].strip()
        if raw_image not in allowed_images:
            raise ValueError(f"Image not allowed: {raw_image}")
        node = formdata.get("node", [""])[0]
        node_ip = formdata.get("node_ip", [""])[0]
        if not node_ip or node_ip in ['127.0.0.1', 'localhost', '0.0.0.0']:
            raise ValueError(f"Invalid node IP: {node_ip}")
        return {"image": allowed_images[raw_image], "node": node, "node_ip": node_ip}

    c.Spawner.options_from_form = options_from_form
    c.Spawner.start_timeout = 600
    c.Spawner.http_timeout = 300
    c.Spawner.poll_interval = 30
    c.Spawner.name_template = "jupyterlab-{username}"
    c.Spawner.debug = True

    # Docker spawner settings
    c.DockerSpawner.image = os.environ.get("DOCKER_NOTEBOOK_IMAGE", "danielcristh0/jupyterlab:cpu")
    c.DockerSpawner.notebook_dir = "/home/jovyan/work"
    c.DockerSpawner.port = 0
    c.DockerSpawner.use_internal_ip = False
    c.DockerSpawner.volumes = {
        "jupyterhub-user-{username}": "/home/jovyan/work",
        "shared-data": "/home/jovyan/shared"
    }
    c.DockerSpawner.cpu_limit = 2.0
    c.DockerSpawner.mem_limit = '4G'

    c.Spawner.default_url = '/lab'
    c.Spawner.disable_user_config = True

    c.DockerSpawner.remove = True  # Remove container when stopped
    c.DockerSpawner.debug = True