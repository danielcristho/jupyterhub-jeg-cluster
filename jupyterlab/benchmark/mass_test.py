import os
import json
import random
import time
import uuid
import websocket
import requests
import argparse
import logging

from locust import HttpUser, task, between, events
from threading import Lock
from requests.exceptions import RequestException, ConnectionError

from dotenv import load_dotenv

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JupyterLoadTest")


load_dotenv()

# Argparse
parser = argparse.ArgumentParser()
parser.add_argument("--jupyterhub-host", default=os.getenv('JUPYTERHUB_HOST', 'http://127.0.0.1'))
parser.add_argument("--jupyterhub-port", default=os.getenv('JUPYTERHUB_PORT', '18000'))
parser.add_argument("--discovery-host", default=os.getenv('DISCOVERY_API_HOST', 'http://127.0.0.1'))
parser.add_argument("--discovery-port", default=os.getenv('DISCOVERY_API_PORT', '15002'))
parser.add_argument("--jeg-host-ip", default=os.getenv('JEG_HOST_IP', '127.0.0.1'))
parser.add_argument("--jeg-port", default=os.getenv('JEG_PORT', '8889'))
parser.add_argument("--jeg-auth-token", default=os.getenv('JEG_AUTH_TOKEN'))
args, _ = parser.parse_known_args()

JUPYTERHUB_URL = f"{args.jupyterhub_host}:{args.jupyterhub_port}"
DISCOVERY_API_URL = f"{args.discovery_host}:{args.discovery_port}"
JEG_HOST_IP = args.jeg_host_ip
JEG_PORT = args.jeg_port
JEG_AUTH_TOKEN = args.jeg_auth_token

# Virtual users (username and password)
TEST_USERS = [(f"testuser{i}", f"testuser{i}") for i in range(1, 11)] + \
             [(f"random{i}", "randomuser@00") for i in range(1, 11)]

user_credentials = TEST_USERS[:]
random.shuffle(user_credentials)
credentials_lock = Lock()

class JupyterHubUser(HttpUser):
    host = JUPYTERHUB_URL
    wait_time = between(5, 15)

    def on_start(self):
        global user_credentials
        with credentials_lock:
            if not user_credentials:
                logger.warning("No more credentials available. Quitting...")
                self.environment.runner.quit()
                return
            self.username, self.password = user_credentials.pop()

        self.kernel_id = None
        self.server_running = False

        try:
            # Get CSRF token
            with self.client.get("/hub/login", name="GET /hub/login", catch_response=True) as r:
                self.xsrf_token = r.cookies.get("_xsrf")
                if not self.xsrf_token:
                    r.failure("Missing _xsrf token.")
                    self.environment.runner.quit()
                    return

            # Login
            with self.client.post(
                "/hub/login",
                data={"username": self.username, "password": self.password, "_xsrf": self.xsrf_token},
                catch_response=True,
                allow_redirects=False
            ) as login_response:
                if login_response.status_code == 302:
                    self.jupyterhub_session_id = login_response.cookies.get("jupyterhub-session-id")
                else:
                    login_response.failure(f"Login failed. Status: {login_response.status_code}")
                    self.environment.runner.quit()

        except Exception as e:
            logger.error(f"[{self.username}] Login error: {e}", exc_info=True)
            self.environment.runner.quit()

    @task
    def full_user_journey(self):
        if not self.username:
            return

        try:
            # Get profiles
            with self.client.get(f"{DISCOVERY_API_URL}/profiles", name="GET /profiles", catch_response=True) as r:
                if r.status_code != 200:
                    r.failure("Failed to get profiles.")
                    return
                profiles = r.json().get("profiles", [])
                selected = next((p for p in profiles if p["name"] == "single-cpu"), None) or profiles[0]

            # Select node
            payload = {
                "profile_id": selected["id"],
                "num_nodes": 1,
                "user_id": self.username
            }
            with self.client.post(f"{DISCOVERY_API_URL}/select-nodes", json=payload, name="POST /select-nodes", catch_response=True) as r:
                if r.status_code != 200:
                    r.failure("Failed to select nodes.")
                    return
                nodes = r.json().get("selected_nodes", [])
                if not nodes:
                    r.failure("No nodes returned.")
                    return

            node = nodes[0]["hostname"]

            # Spawn server
            csrf = self.client.cookies.get("_xsrf")
            spawn_data = {
                "profile_id": selected["id"],
                "profile_name": selected["name"],
                "image": "danielcristh0/jupyterlab:cpu",
                "node_count_final": 1,
                "primary_node": node,
                "selected_nodes": json.dumps(nodes),
                "_xsrf": csrf
            }
            with self.client.post("/hub/spawn", data=spawn_data, name="POST /hub/spawn", catch_response=True) as r:
                if r.status_code != 302:
                    r.failure(f"Spawn failed. Status: {r.status_code}")
                    return

            self._wait_for_server_ready()

        except Exception as e:
            logger.error(f"[{self.username}] Journey error: {e}", exc_info=True)
            self.environment.runner.quit()
        finally:
            self.cleanup()

    def _wait_for_server_ready(self, timeout=300):
        logger.info(f"[{self.username}] Waiting for server to be ready...")
        start = time.time()
        self.client.headers["X-XSRFToken"] = self.xsrf_token
        self.client.cookies.set("jupyterhub-session-id", self.jupyterhub_session_id, domain=self.host.split("://")[-1].split(":")[0])

        while time.time() - start < timeout:
            try:
                with self.client.get(f"/hub/api/users/{self.username}/server/progress", name="GET /server/progress", catch_response=True) as r:
                    if r.status_code == 200 and r.json().get("ready"):
                        self.server_running = True
                        logger.info(f"[{self.username}] Server is ready.")
                        return
                    elif r.status_code == 404 and time.time() - start < 10:
                        continue
                    elif r.status_code != 200:
                        r.failure("Error during server progress polling.")
                        return
            except Exception:
                pass
            time.sleep(5)

        logger.error(f"[{self.username}] Timeout waiting for server.")
        self.server_running = False
        events.request.fire(
            request_type="spawn",
            name="timeout",
            response_time=timeout * 1000,
            response_length=0,
            exception=Exception("Spawn Timeout")
        )

    def cleanup(self):
        if self.kernel_id:
            try:
                self.client.delete(f"/user/{self.username}/api/kernels/{self.kernel_id}", name="DELETE /api/kernels")
                self.kernel_id = None
            except Exception as e:
                logger.warning(f"[{self.username}] Failed to delete kernel: {e}")

        if self.server_running:
            try:
                self.client.delete(f"/hub/api/users/{self.username}/server", name="DELETE /server")
                self.server_running = False
            except Exception as e:
                logger.warning(f"[{self.username}] Failed to stop server: {e}")

    def on_stop(self):
        logger.info(f"[{self.username}] Stopping and cleaning up.")
        self.cleanup()