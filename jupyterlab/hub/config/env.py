"""Loads environment variables from .env"""
import os
from dotenv import load_dotenv

def load_environment(c):
    load_dotenv()
    required_env = ["CONFIGPROXY_AUTH_TOKEN", "JUPYTERHUB_ADMIN"]
    missing = [key for key in required_env if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
