"""Hub configuration"""

import os

def configure_hub(c):
    """Configure JupyterHub hub settings"""

    c.JupyterHub.hub_bind_url = 'http://0.0.0.0:8081'

    c.JupyterHub.hub_ip = 'hub'

    c.JupyterHub.db_url = 'sqlite:///data/jupyterhub.sqlite'

    # Cookie and security
    c.JupyterHub.cookie_secret_file = 'data/jupyterhub_cookie_secret'

    c.JupyterHub.log_level = 'DEBUG'

    c.JupyterHub.shutdown_on_logout = True
    c.JupyterHub.cleanup_servers = True

    c.JupyterHub.allow_named_servers = False

    c.JupyterHub.base_url = '/'
    c.JupyterHub.default_url = '/hub/home'