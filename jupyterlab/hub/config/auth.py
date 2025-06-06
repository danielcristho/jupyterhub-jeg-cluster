"""
Handle Authenctication

- Using nativeauthenticator
"""

import os

def configure_auth(c):
    c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"
    c.Authenticator.allow_all = True
    c.NativeAuthenticator.open_signup = True
    c.NativeAuthenticator.minimum_password_length = 8
    c.NativeAuthenticator.enable_signup = True
    c.Authenticator.admin_users = set(os.environ.get("JUPYTERHUB_ADMIN", "").split(","))
