"""JupyterHub Configuration"""

import os
import sys

def configure_hub(c):
    """Configure core settings for JupyterHub."""

    # === Hub Network Binding ===
    c.JupyterHub.hub_bind_url = 'http://0.0.0.0:18000'  # Hub internal binding URL
    c.JupyterHub.hub_ip = 'hub'                        # Docker internal hostname
    c.JupyterHub.ip = '0.0.0.0'                         # Bind to all interfaces
    c.JupyterHub.port = 18000                           # Hub listening port

    # === Base URL and Routing ===
    c.JupyterHub.base_url = '/'                         # Root URL prefix
    c.JupyterHub.default_url = '/hub/home'              # Redirect after login

    # === Cookie & Session ===
    c.JupyterHub.cookie_secret_file = 'data/jupyterhub_cookie_secret'

    # === Logging & Behavior ===
    c.JupyterHub.log_level = 'DEBUG'                    # Verbose logging for debugging
    c.JupyterHub.shutdown_on_logout = True              # Shutdown user servers on logout
    c.JupyterHub.cleanup_servers = True                 # Clean up servers on restart
    c.JupyterHub.allow_named_servers = False            # Disable named servers per user

    # === Database Configuration ===
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT")
    db_user = os.getenv("POSTGRES_USER")
    db_pass = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB")

    c.JupyterHub.db_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    # sqlite fallbck
    # c.JupyterHub.db_url = 'sqlite:///data/jupyterhub.sqlite'

    # === Additional services ===
    c.JupyterHub.metrics_enabled = True        

    c.JupyterHub.services = [
        {
            'name': 'prometheus-service',
            'admin': True,  # Allows Prometheus to access admin metrics endpoint
        },
        {
            'name': 'jupyterhub-idle-culler-service',
            'admin': True,
            'command': [
                sys.executable,
                '-m', 'jupyterhub_idle_culler',
                '--timeout=600',  # Auto-shutdown idle servers after 10 minutes
            ],
        },
    ]
