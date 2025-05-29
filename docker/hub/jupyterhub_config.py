"""Main jupyterhub config file"""
from config.env import load_environment
from config.hub import configure_hub
from config.spawner import configure_spawner
from config.proxy import configure_proxy
from config.auth import configure_auth
from config.hooks import attach_hooks

load_environment(c)
configure_hub(c)
configure_spawner(c)
configure_proxy(c)
configure_auth(c)
attach_hooks()

