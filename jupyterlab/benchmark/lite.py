import time
import uuid
from locust import HttpUser, task, between

class JupyterHubUser(HttpUser):
    wait_time = between(1, 5)

    username = None
    server_name = None
    kernel_id = None

    def on_start(self):
        """
        """
        self.username = f"halo-{uuid.uuid4()}"

        password = "your-password" 
        self.client.post("/hub/login", {
            "username": self.username,
            "password": password
        })

        print(f"Pengguna {self.username} telah login dan akan memulai server.")
        self.start_server_and_kernel()

    def start_server_and_kernel(self):
        """
        """
        with self.client.get(f"/hub/spawn/{self.username}", catch_response=True, name="/hub/spawn/[username]") as response:
            if response.status_code == 200:
                print(f"Server untuk {self.username} berhasil dimulai.")
            else:
                print(f"Gagal memulai server untuk {self.username}. Status: {response.status_code}")
                response.failure("Gagal memulai server")
                return

        with self.client.post(f"/user/{self.username}/api/kernels", 
                                json={"name": "python3-worker2"},
                                catch_response=True,
                                name="/user/[username]/api/kernels") as response:
            if response.status_code == 201:
                kernel_data = response.json()
                self.kernel_id = kernel_data.get("id")
                print(f"Kernel {self.kernel_id} berhasil dibuat untuk {self.username}.")
            else:
                print(f"Gagal membuat kernel untuk {self.username}. Status: {response.status_code}")
                response.failure("Gagal membuat kernel")

    @task
    def execute_code(self):
        """
        """
        if not self.kernel_id:
            print(f"Pengguna {self.username} tidak memiliki kernel, melewatkan eksekusi.")
            return

        code_to_run = "import time; time.sleep(0.5); a = 1+1; print(a)"

        with self.client.get(f"/user/{self.username}/api/contents", name="/user/[username]/api/contents", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Gagal mengakses isi konten.")

    def on_stop(self):
        """
        """
        if self.kernel_id:
            self.client.delete(f"/user/{self.username}/api/kernels/{self.kernel_id}", name="/user/[username]/api/kernels/[kernel_id]")
            print(f"Kernel {self.kernel_id} untuk {self.username} dihapus.")

        # Hapus server
        self.client.delete(f"/hub/api/users/{self.username}/server", name="/hub/api/users/[username]/server")
        print(f"Server untuk {self.username} dihapus.")