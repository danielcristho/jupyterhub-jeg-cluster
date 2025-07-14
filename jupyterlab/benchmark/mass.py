import os
import json
import random
import time
from locust import HttpUser, task, between, events
from threading import Lock
from requests.exceptions import RequestException
import requests
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--jupyterhub-url", default=os.getenv('JUPYTERHUB_URL', 'http://10.33.17.30:18000'))
parser.add_argument("--discovery-url", default=os.getenv('DISCOVERY_API_URL', 'http://10.33.17.30:15002'))
args, unknown = parser.parse_known_args()

JUPYTERHUB_URL = args.jupyterhub_url
DISCOVERY_API_URL = args.discovery_url

TEST_USERS = [
    (f"testuser{i}", f"testuser{i}") for i in range(1, 11)
] + [
    (f"random{i}", "randomuser@00") for i in range(1, 11)
]

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
                print("Tidak ada lagi kredensial user. Menghentikan user.")
                self.environment.runner.quit()
                return
            self.username, self.password = user_credentials.pop()

        self.server_running = False
        self.kernel_id = None

        print(f"[{self.username}] Memulai virtual user...")

        try:
            self.client.get("/hub/login", name="/hub/login [GET]")

            csrf_token = self.client.cookies.get("_xsrf")
            if not csrf_token:
                print(f"[{self.username}] Gagal mendapatkan token CSRF.")
                self.environment.runner.quit()
                return

            with self.client.post(
                "/hub/login",
                data={"username": self.username, "password": self.password, "_xsrf": csrf_token},
                catch_response=True
            ) as login_response:
                if login_response.status_code != 302:
                    login_response.failure(f"Gagal login user {self.username}. Status: {login_response.status_code}, Resp: {login_response.text}")
                    return

            print(f"[{self.username}] Login berhasil.")

        except RequestException as e:
            print(f"[{self.username}] Error koneksi login: {e}")
            self.environment.runner.quit()

    @task
    def full_user_journey(self):
        try:
            print(f"[{self.username}] Mulai proses pemilihan profil...")

            profiles_resp = requests.get(f"{DISCOVERY_API_URL}/profiles")
            profiles_resp.raise_for_status()
            profiles = profiles_resp.json().get('profiles', [])
            if not profiles:
                print(f"[{self.username}] Tidak ada profil tersedia.")
                return

            selected_profile = next((p for p in profiles if p['name'] == 'multi-cpu'), profiles[0])

            nodes_resp = requests.post(f"{DISCOVERY_API_URL}/select-nodes", json={
                "profile_id": selected_profile['id'],
                "num_nodes": 1,
                "user_id": self.username
            })
            nodes_resp.raise_for_status()
            selected_nodes_data = nodes_resp.json()
            if not selected_nodes_data.get("selected_nodes"):
                print(f"[{self.username}] Gagal memilih node.")
                return

            print(f"[{self.username}] Node dan profil siap.")
            current_csrf_token = self.client.cookies.get("_xsrf")

            spawn_form_data = {
                "profile_id": selected_profile['id'],
                "profile_name": selected_profile['name'],
                "image": "danielcristh0/jupyterlab:cpu",
                "node_count_final": 1,
                "primary_node": selected_nodes_data['selected_nodes'][0]['hostname'],
                "selected_nodes": json.dumps(selected_nodes_data['selected_nodes']),
                "_xsrf": current_csrf_token
            }

            print(f"[{self.username}] Mengirim permintaan spawn...")
            with self.client.post("/hub/spawn", data=spawn_form_data, catch_response=True) as spawn_req:
                if spawn_req.status_code != 302:
                    spawn_req.failure(f"Spawn gagal. Status: {spawn_req.status_code}, Resp: {spawn_req.text}")
                    return

            self._wait_for_server_ready()
            if not self.server_running:
                return

            print(f"[{self.username}] Server siap. Membuat kernel...")
            self.client.headers['X-XSRFToken'] = self.client.cookies.get("_xsrf")
            kernel_resp = self.client.post(f"/user/{self.username}/api/kernels", json={"name": "python3"})
            if kernel_resp.status_code == 201:
                self.kernel_id = kernel_resp.json()['id']
                print(f"[{self.username}] Kernel dibuat: {self.kernel_id}")
            else:
                print(f"[{self.username}] Gagal membuat kernel. Status: {kernel_resp.status_code}")

            time.sleep(random.uniform(10, 20))

        finally:
            self.cleanup()

    def _wait_for_server_ready(self, timeout=300):
        print(f"[{self.username}] Menunggu server siap...")
        start_time = time.time()
        self.client.headers['X-XSRFToken'] = self.client.cookies.get("_xsrf")
        while time.time() - start_time < timeout:
            try:
                with self.client.get(f"/hub/api/users/{self.username}/server/progress", catch_response=True, name="/hub/api/users/[user]/server/progress") as r:
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("ready"):
                            print(f"[{self.username}] Server berhasil di-spawn.")
                            self.server_running = True
                            return
                        print(f"[{self.username}] Status spawn: {data.get('message', '...')}")
                    else:
                        r.failure(f"Gagal polling spawn. Status: {r.status_code}")
                        return
            except RequestException as e:
                print(f"[{self.username}] Exception polling: {e}")
            time.sleep(5)

        print(f"[{self.username}] Timeout server.")
        events.request.fire(request_type="spawn", name="timeout", response_time=timeout*1000, response_length=0, exception=Exception("Spawn Timeout"))

    def cleanup(self):
        self.client.headers['X-XSRFToken'] = self.client.cookies.get("_xsrf")
        if self.kernel_id:
            print(f"[{self.username}] Menghapus kernel {self.kernel_id}...")
            self.client.delete(f"/user/{self.username}/api/kernels/{self.kernel_id}", name="/user/[user]/api/kernels/[id]")
            self.kernel_id = None

        if self.server_running:
            print(f"[{self.username}] Menghentikan server...")
            stop_resp = self.client.delete(f"/hub/api/users/{self.username}/server", name="/hub/api/users/[user]/server")
            if stop_resp.status_code not in [202, 204]:
                print(f"[{self.username}] Gagal menghentikan server. Status: {stop_resp.status_code}, Resp: {stop_resp.text}")
            self.server_running = False

    def on_stop(self):
        print(f"[{self.username}] Cleanup stopped user...")
        self.cleanup()
