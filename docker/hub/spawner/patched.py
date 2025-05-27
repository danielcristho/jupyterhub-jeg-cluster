from .base import MultiNodeSpawner
from traitlets import Bool, Unicode

class PatchedMultiNodeSpawner(MultiNodeSpawner):
    use_external_server_url = Bool(True).tag(config=True)
    server_ip = Unicode("").tag(config=True)
    server_port = Unicode("").tag(config=True)

    @property
    def server_url(self):
        if self.use_external_server_url and self.server_ip and self.server_port:
            return f"http://{self.server_ip}:{self.server_port}"
        return super().server_url