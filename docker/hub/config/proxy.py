"""Proxy config"""

import os

def configure_proxy(c):
    c.JupyterHub.proxy_class = 'jupyterhub.proxy.ConfigurableHTTPProxy'

    c.ConfigurableHTTPProxy.should_start = False
    c.ConfigurableHTTPProxy.api_url = 'http://proxy:8001'
    c.ConfigurableHTTPProxy.auth_token = os.environ["CONFIGPROXY_AUTH_TOKEN"]
    c.ConfigurableHTTPProxy.debug = True
    c.ConfigurableHTTPProxy.request_timeout = 30