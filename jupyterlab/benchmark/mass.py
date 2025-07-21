import os
import json
import random
import time
import uuid
import websocket
import requests
import argparse
from locust import HttpUser, task, between, events
from threading import Lock
from requests.exceptions import RequestException, ConnectionError

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--jupyterhub-url", default=os.getenv('JUPYTERHUB_URL', 'http://10.33.17.30:18000'), help="The base URL for JupyterHub.")
parser.add_argument("--discovery-url", default=os.getenv('DISCOVERY_API_URL', 'http://10.33.17.30:15002'), help="The base URL for the Discovery Service API.")
parser.add_argument("--jeg-host-ip", default=os.getenv('JEG_HOST_IP', '10.33.17.30'), help="The host IP where JEG is running (for WebSocket connections).")
parser.add_argument("--jeg-port", default=os.getenv('JEG_PORT', '8889'), help="The port where JEG is running (for WebSocket connections).")
parser.add_argument("--jeg-auth-token", default=os.getenv('JEG_AUTH_TOKEN', 'jeg-jeg-an'), help="Authentication token for JEG.")
args, unknown = parser.parse_known_args()

JUPYTERHUB_URL = args.jupyterhub_url
DISCOVERY_API_URL = args.discovery_url
JEG_HOST_IP = args.jeg_host_ip
JEG_PORT = args.jeg_port
JEG_AUTH_TOKEN = args.jeg_auth_token

TARGET_OVERLOAD_KERNELSPEC = "python3-docker-rpl" 
NUM_INITIAL_OVERLOAD_USERS = 3 

TEST_USERS = [
    (f"testuser{i}", f"testuser{i}") for i in range(1, 11)
] + [
    (f"randomuser{i}", f"randomuser{i}") for i in range(1, 11)
]

user_credentials = TEST_USERS[:]
random.shuffle(user_credentials)
credentials_lock = Lock()

user_counter = 0
user_counter_lock = Lock()

def run_code_in_kernel(jeg_base_url_ws: str, username: str, kernel_id: str, code: str, jeg_auth_token: str) -> bool:
    """
    Executes a given code snippet in a remote Jupyter kernel via WebSocket.
    """
    ws_url = f"ws://{jeg_base_url_ws}/api/kernels/{kernel_id}/channels"
    logger.info(f"[{username}] Attempting to connect to kernel WebSocket: {ws_url}")

    msg_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    ws_headers_list = [
        f"Authorization: token {jeg_auth_token}",
        f"Origin: http://{jeg_base_url_ws.split(':')[0]}" 
    ]

    ws = None
    start_time = time.time()
    try:
        ws = websocket.create_connection(ws_url, header=ws_headers_list, timeout=15)
        logger.info(f"[{username}] Connected to kernel WebSocket {kernel_id}.")

        msg = {
            "header": {
                "msg_id": msg_id,
                "username": username,
                "session": session_id,
                "msg_type": "execute_request",
                "version": "5.3"
            },
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True
            }
        }

        ws.send(json.dumps(msg))
        logger.debug(f"[{username}] Execution message sent for kernel {kernel_id}.")

        output_buffer = []
        timeout_seconds = 240 
        end_wait_time = time.time() + timeout_seconds
        
        while time.time() < end_wait_time:
            try:
                res = json.loads(ws.recv()) 
                
                if res.get("msg_type") == "stream":
                    output_buffer.append(res["content"].get("text", ""))
                elif res.get("msg_type") == "execute_result":
                    output_buffer.append(str(res["content"].get("data", {}).get("text/plain", "")))
                elif res.get("msg_type") == "error":
                    error_msg = f"ERROR: {res['content'].get('ename', '')}: {res['content'].get('evalue', '')}"
                    output_buffer.append(error_msg)
                    logger.error(f"[{username}] Kernel Error: {res['content'].get('traceback', [])}")
                    raise Exception(f"Kernel execution error: {error_msg}")
                elif res.get("msg_type") == "status" and res["content"].get("execution_state") == "idle":
                    logger.info(f"[{username}] Kernel execution completed (idle). Output: {''.join(output_buffer).strip()[:200]}...")
                    break
                elif res.get("msg_type") == "shutdown_reply":
                    logger.warning(f"[{username}] Kernel shutdown reply received for {kernel_id}.")
                    break
            except websocket.WebSocketTimeoutException:
                continue 
            except Exception as e:
                logger.error(f"[{username}] Error reading from WebSocket: {e}", exc_info=True)
                raise e

        if time.time() >= end_wait_time:
            raise TimeoutError(f"[{username}] Timeout waiting for kernel {kernel_id} to become idle after {timeout_seconds}s.")

        events.request.fire(request_type="WS", name="kernel_execution", response_time=(time.time() - start_time) * 1000, response_length=len("".join(output_buffer)))
        logger.info(f"[{username}] Code successfully executed on kernel {kernel_id}.")
        return True

    except (websocket.WebSocketException, ConnectionError) as e:
        events.request.fire(request_type="WS", name="kernel_connect_fail", response_time=(time.time() - start_time) * 1000, response_length=0, exception=e)
        logger.error(f"[{username}] Failed to connect/communicate via WebSocket to kernel {kernel_id}: {e}", exc_info=True)
        return False
    except TimeoutError as e:
        events.request.fire(request_type="WS", name="kernel_execution_timeout", response_time=(time.time() - start_time) * 1000, response_length=0, exception=e)
        logger.error(f"[{username}] Timeout while waiting for kernel execution {kernel_id}: {e}", exc_info=True)
        return False
    except Exception as e:
        events.request.fire(request_type="WS", name="kernel_execution_general_fail", response_time=(time.time() - start_time) * 1000, response_length=0, exception=e)
        logger.error(f"[{username}] Unexpected error during code execution on kernel {kernel_id}: {e}", exc_info=True)
        return False
    finally:
        if ws:
            ws.close()
            logger.debug(f"[{username}] WebSocket to kernel {kernel_id} closed.")

class JupyterHubUser(HttpUser):
    host = JUPYTERHUB_URL
    wait_time = between(5, 15)

    def on_start(self):
        """Initializes a new user session, logs in, and sets user flags."""
        global user_credentials
        self.username = None
        self.password = None
        
        with credentials_lock:
            if user_credentials:
                self.username, self.password = user_credentials.pop(0) 
            else:
                logger.warning("No more user credentials available. Stopping user.")
                self.environment.runner.quit()
                return

        self.server_running = False
        self.kernel_id = None
        self.jupyterhub_session_id = None
        self.xsrf_token = None
        self.is_overload_user = False 

        with user_counter_lock:
            global user_counter
            if user_counter < NUM_INITIAL_OVERLOAD_USERS:
                self.is_overload_user = True
                user_counter += 1
                logger.info(f"[{self.username}] Designated as an overload user ({user_counter}/{NUM_INITIAL_OVERLOAD_USERS}).")
            else:
                logger.info(f"[{self.username}] Starting as a regular virtual user.")

        try:
            with self.client.get("/hub/login", name="/hub/login [GET]", catch_response=True) as r:
                self.xsrf_token = r.cookies.get("_xsrf") 
                if not self.xsrf_token:
                    logger.error(f"[{self.username}] Failed to get CSRF token from GET login page.")
                    r.failure(f"No XSRF token from GET login page.")
                    self.environment.runner.quit()
                    return

            with self.client.post(
                "/hub/login",
                data={"username": self.username, "password": self.password, "_xsrf": self.xsrf_token},
                catch_response=True,
                allow_redirects=False, 
                name="/hub/login [POST]" 
            ) as login_response:
                if login_response.status_code == 302:
                    logger.info(f"[{self.username}] Login successful (received 302 redirect).")
                    self.jupyterhub_session_id = login_response.cookies.get("jupyterhub-session-id")
                    if not self.jupyterhub_session_id:
                        logger.warning(f"[{self.username}] jupyterhub-session-id not directly found after POST login (expected if redirect is not followed).")
                else: 
                    login_response.failure(f"Failed to log in user {self.username}. Status: {login_response.status_code}, Resp: {login_response.text}")
                    self.environment.runner.quit()
                    return
            
        except (RequestException, ConnectionError) as e:
            logger.error(f"[{self.username}] Connection error during on_start: {e}", exc_info=True)
            self.environment.runner.quit()
        except Exception as e:
            logger.error(f"[{self.username}] Unexpected error in on_start: {e}", exc_info=True)
            self.environment.runner.quit()

    @task
    def full_user_journey(self):
        """Simulates a full user journey: profile/node selection, server spawn, kernel creation, and code execution."""
        if not self.username: 
            return

        try:
            logger.info(f"[{self.username}] Starting profile selection process...")

            with self.client.get(f"{DISCOVERY_API_URL}/profiles", catch_response=True, name="DiscoveryAPI/profiles") as profiles_resp:
                if profiles_resp.status_code != 200:
                    profiles_resp.failure(f"Failed to get profiles from Discovery API. Status: {profiles_resp.status_code}")
                    return
                profiles = profiles_resp.json().get('profiles', [])
                if not profiles:
                    logger.warning(f"[{self.username}] No profiles available from Discovery API.")
                    return
                
                if self.is_overload_user:
                    selected_profile = next((p for p in profiles if p['name'] == 'multi-cpu'), None) 
                    if not selected_profile:
                        logger.error(f"[{self.username}] 'multi-cpu' profile not found for overload user.")
                        self.environment.runner.quit()
                        return
                    logger.info(f"[{self.username}] Selected high-load profile: {selected_profile['name']}")
                else:
                    selected_profile = next((p for p in profiles if p['name'] == 'single-cpu'), None)
                    if not selected_profile:
                        logger.error(f"[{self.username}] 'single-cpu' profile not found for regular user.")
                        self.environment.runner.quit()
                        return
                    logger.info(f"[{self.username}] Selected regular profile: {selected_profile['name']}")

            selected_nodes_data_for_spawn = {} 
            if self.is_overload_user:
                all_nodes_resp = self.client.get(f"{DISCOVERY_API_URL}/all-nodes", name="DiscoveryAPI/all-nodes")
                all_nodes_resp.raise_for_status()
                all_nodes = all_nodes_resp.json().get('nodes', [])
                
                target_hostname = TARGET_OVERLOAD_KERNELSPEC.replace("python3-docker-", "")
                target_node_info = next((n for n in all_nodes if n['hostname'] == target_hostname), None)
                
                if not target_node_info:
                    logger.error(f"[{self.username}] Target overload node '{target_hostname}' not found in Discovery API /all-nodes. Stopping user.")
                    self.environment.runner.quit()
                    return

                selected_nodes_data_for_spawn = {
                    "selected_nodes": [target_node_info],
                    "primary_node_hostname": target_node_info['hostname']
                }
                logger.info(f"[{self.username}] Overload user attempting to stress node: {target_node_info['hostname']}")
            else:
                with self.client.post(f"{DISCOVERY_API_URL}/select-nodes", json={
                    "profile_id": selected_profile['id'],
                    "num_nodes": 1,
                    "user_id": self.username
                }, catch_response=True, name="DiscoveryAPI/select-nodes") as nodes_resp:
                    if nodes_resp.status_code != 200:
                        nodes_resp.failure(f"Failed to select node from Discovery API. Status: {nodes_resp.status_code}")
                        return
                    selected_nodes_data_for_spawn = nodes_resp.json()
                    if not selected_nodes_data_for_spawn.get("selected_nodes"):
                        nodes_resp.failure(f"Discovery API did not return selected nodes: {selected_nodes_data_for_spawn}")
                        return
                logger.info(f"[{self.username}] Node selected by Discovery Service: {selected_nodes_data_for_spawn['selected_nodes'][0]['hostname']}")
            
            with self.client.get(f"/hub/spawn/{self.username}", name=f"/hub/spawn/{self.username} [GET]", catch_response=True) as r:
                self.xsrf_token = r.cookies.get("_xsrf")
                self.jupyterhub_session_id = r.cookies.get("jupyterhub-session-id")

            if not self.xsrf_token:
                logger.error(f"[{self.username}] Failed to get CSRF token before submitting spawn form (GET /hub/spawn).")
                return

            spawn_form_data = {
                "profile_id": selected_profile['id'],
                "profile_name": selected_profile['name'],
                "image": "danielcristh0/jupyterlab:cpu", 
                "node_count_final": 1,
                "primary_node": selected_nodes_data_for_spawn['selected_nodes'][0]['hostname'],
                "selected_nodes": json.dumps(selected_nodes_data_for_spawn['selected_nodes']),
                "_xsrf": self.xsrf_token
            }

            logger.info(f"[{self.username}] Sending JupyterLab spawn request...")
            with self.client.post(
                "/hub/spawn",
                data=spawn_form_data,
                catch_response=True,
                name="/hub/spawn [POST]"
            ) as spawn_req:
                if spawn_req.status_code != 302:
                    spawn_req.failure(f"Spawn failed. Status: {spawn_req.status_code}, Resp: {spawn_req.text}")
                    return

            self._wait_for_server_ready()
            if not self.server_running:
                logger.error(f"[{self.username}] Server not ready, skipping kernel execution.")
                return

            logger.info(f"[{self.username}] Server ready. Creating JEG kernel...")
            self.client.headers['X-XSRFToken'] = self.xsrf_token 
            
            if self.is_overload_user:
                KERNEL_SPEC_NAME = TARGET_OVERLOAD_KERNELSPEC 
                logger.info(f"[{self.username}] Overload user requesting kernel: {KERNEL_SPEC_NAME}")
            else:
                KERNEL_SPEC_NAME = f"python3-docker-{selected_nodes_data_for_spawn['selected_nodes'][0]['hostname']}"
                logger.info(f"[{self.username}] Regular user requesting kernel: {KERNEL_SPEC_NAME}")

            with self.client.post(f"/user/{self.username}/api/kernels", json={"name": KERNEL_SPEC_NAME}, catch_response=True, name="/user/[user]/api/kernels [POST]") as kernel_resp:
                if kernel_resp.status_code == 201:
                    self.kernel_id = kernel_resp.json()['id']
                    logger.info(f"[{self.username}] JEG kernel created: {self.kernel_id}")
                else:
                    kernel_resp.failure(f"Failed to create JEG kernel. Status: {kernel_resp.status_code}, Resp: {kernel_resp.text}")
                    return

            code_to_execute = ""
            if self.is_overload_user:
                code_to_execute = """
import numpy as np
import time
import os
import platform

print("Starting largest computation")
MATRIX_SIZE = 10000 
A = np.random.rand(MATRIX_SIZE, MATRIX_SIZE) 
B = np.random.rand(MATRIX_SIZE, MATRIX_SIZE)
start = time.time()
C = np.matmul(A, B)
end = time.time()
print("Done. Overload execution time: {:.2f} seconds".format(end - start))
print(f"Overload kernel hostname: {os.uname().nodename}")
print(f"Overload kernel platform: {platform.platform()}")
time.sleep(20) 
"""
            else:
                code_to_execute = """
import numpy as np
import time
import os
import platform

print("Starting moderate matrix computation...")
MATRIX_SIZE = 5000 
A = np.random.rand(MATRIX_SIZE, MATRIX_SIZE) 
B = np.random.rand(MATRIX_SIZE, MATRIX_SIZE)
start = time.time()
C = np.matmul(A, B)
end = time.time()
print("Done. Normal execution time: {:.2f} seconds".format(end - start))
print(f"Normal kernel hostname: {os.uname().nodename}")
print(f"Normal kernel platform: {platform.platform()}")
time.sleep(5) 
"""

            jeg_base_url_for_ws = f"{JEG_HOST_IP}:{JEG_PORT}"
            
            logger.info(f"[{self.username}] Sending code to kernel {self.kernel_id} (Overload: {self.is_overload_user})...")
            run_code_in_kernel(
                jeg_base_url_for_ws,
                self.username,
                self.kernel_id,
                code_to_execute,
                JEG_AUTH_TOKEN
            )

            time.sleep(random.uniform(5, 10)) 
            
        except (RequestException, ConnectionError) as e:
            logger.error(f"[{self.username}] Error during user journey: {e}", exc_info=True)
            self.environment.runner.quit() 
        except Exception as e:
            logger.error(f"[{self.username}] Unexpected error during user journey: {e}", exc_info=True)
            self.environment.runner.quit()
        finally:
            self.cleanup()

    def _wait_for_server_ready(self, timeout: int = 300):
        """Polls the JupyterHub API, waiting for the user's server to become ready."""
        logger.info(f"[{self.username}] Waiting for JupyterLab server to be ready...")
        start_time = time.time()
        self.client.headers['X-XSRFToken'] = self.xsrf_token
        self.client.cookies.set("jupyterhub-session-id", self.jupyterhub_session_id, domain=self.host.split('://')[-1].split(':')[0])

        while time.time() - start_time < timeout:
            try:
                with self.client.get(f"/hub/api/users/{self.username}/server/progress", catch_response=True, name="/hub/api/users/[user]/server/progress") as r:
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("ready"):
                            logger.info(f"[{self.username}] JupyterLab server successfully spawned and ready.")
                            self.server_running = True
                            return
                        logger.info(f"[{self.username}] Spawn status: {data.get('message', '...')}")
                    elif r.status_code == 404 and time.time() - start_time > 10: 
                        logger.warning(f"[{self.username}] Server progress 404, possibly still in early initialization. Retrying.")
                    else:
                        r.failure(f"Failed polling spawn. Status: {r.status_code}, Resp: {r.text}")
                        return
            except (RequestException, ConnectionError) as e:
                logger.warning(f"[{self.username}] Exception polling spawn: {e}", exc_info=True)
            except json.JSONDecodeError:
                logger.error(f"[{self.username}] Failed to decode JSON from progress response: {r.text}", exc_info=True)
                return
            time.sleep(5) 

        logger.error(f"[{self.username}] Timeout waiting for JupyterLab server to be ready after {timeout} seconds.")
        events.request.fire(request_type="spawn", name="timeout_server_ready", response_time=timeout*1000, response_length=0, exception=Exception("Spawn Timeout"))
        self.server_running = False

    def cleanup(self):
        """Cleans up resources by deleting the kernel and stopping the JupyterLab server."""
        self.client.headers['X-XSRFToken'] = self.xsrf_token if self.xsrf_token else ""
        self.client.cookies.set("jupyterhub-session-id", self.jupyterhub_session_id, domain=self.host.split('://')[-1].split(':')[0])

        if self.kernel_id:
            logger.info(f"[{self.username}] Deleting JEG kernel {self.kernel_id}...")
            try:
                with self.client.delete(f"/user/{self.username}/api/kernels/{self.kernel_id}", catch_response=True, name="/user/[user]/api/kernels/[id] [DELETE]") as r:
                    if r.status_code not in [200, 204]:
                        r.failure(f"Failed to delete kernel {self.kernel_id}. Status: {r.status_code}, Resp: {r.text}")
                self.kernel_id = None
            except (RequestException, ConnectionError) as e:
                logger.error(f"[{self.username}] Error deleting kernel: {e}", exc_info=True)
        
        if self.server_running:
            logger.info(f"[{self.username}] Stopping JupyterLab server...")
            try:
                with self.client.delete(f"/hub/api/users/{self.username}/server", catch_response=True, name="/hub/api/users/[user]/server [DELETE]") as stop_resp:
                    if stop_resp.status_code not in [202, 204]:
                        stop_resp.failure(f"Failed to stop server. Status: {stop_resp.status_code}, Resp: {stop_resp.text}")
                self.server_running = False
            except (RequestException, ConnectionError) as e:
                logger.error(f"[{self.username}] Error stopping server: {e}", exc_info=True)

    def on_stop(self):
        """Called when a user stops. Ensures proper cleanup."""
        logger.info(f"[{self.username}] Cleaning up stopped user...")
        self.cleanup()