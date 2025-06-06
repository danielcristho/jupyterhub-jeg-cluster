"""Integrates server option form and images validation"""

import os
from spawner.multinode import MultiNodeSpawner

def configure_spawner(c):
    c.JupyterHub.spawner_class = MultiNodeSpawner

    # Get the project root directory (parent of config folder)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Configure static files serving
    static_dir = os.path.join(project_root, "src", "static")

    # Add static file handler to JupyterHub
    c.JupyterHub.extra_handlers = [
        (r"/static/(.*)", "tornado.web.StaticFileHandler", {"path": static_dir}),
    ]

    # Load the form template with proper static file references
    form_template_path = os.path.join(project_root, "src", "templates", "form.html")
    css_path = os.path.join(static_dir, "style.css")
    js_path = os.path.join(static_dir, "main.js")

    try:
        # Try to read files and embed them directly (more reliable for JupyterHub)
        with open(form_template_path, 'r', encoding='utf-8') as f:
            form_content = f.read()

        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()

        # Embed CSS and JS directly into HTML
        form_content = form_content.replace(
            '<link rel="stylesheet" href="style.css" />',
            f'<style>{css_content}</style>'
        )
        form_content = form_content.replace(
            '<script src="main.js"></script>',
            f'<script>{js_content}</script>'
        )

        c.Spawner.options_form = form_content

    except FileNotFoundError as e:
        print(f"Error loading form files: {e}")
        # Fallback to basic form if files not found
        c.Spawner.options_form = """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h2>JupyterLab Configuration</h2>
            <p style="color: red;">Error: Form templates not found. Using basic fallback.</p>
            <label for="image">Docker Image:</label>
            <select name="image" required>
                <option value="danielcristh0/jupyterlab:cpu">CPU Image (Basic)</option>
                <option value="danielcristh0/jupyterlab:gpu">GPU Image (ML/AI)</option>
            </select>
        </div>
        """

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
        profile_id = formdata.get("profile_id", [""])[0]
        session_config = formdata.get("session_config", [""])[0]

        # Basic validation
        if not node_ip or node_ip in ['127.0.0.1', 'localhost', '0.0.0.0']:
            raise ValueError(f"Invalid node IP: {node_ip}")

        options = {
            "image": allowed_images[raw_image],
            "node": node,
            "node_ip": node_ip
        }

        # Add profile and session config if provided
        if profile_id:
            options["profile_id"] = profile_id
        if session_config:
            options["session_config"] = session_config

        return options

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