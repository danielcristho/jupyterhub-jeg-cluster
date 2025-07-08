# jeg_config.py yang disederhanakan
import os

c = get_config()

# c.EnterpriseGatewayApp.kernel_spec_dirs = ['/usr/local/share/jupyter/kernels']

c.BaseProcessProxy.response_address = '192.168.122.1'

c.EnterpriseGatewayApp.remote_hosts = ['192.168.122.99', '192.168.122.98']

# c.DistributedProcessProxy.ssh_key_filename = '/home/jovyan/.ssh/id_rsa'

c.DistributedProcessProxy.disable_host_key_checking = True

c.Application.log_format = '[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s] %(message)s'

print("[INFO] JEG config loaded successfully. Using simplified configuration.")
print(f"[INFO] Default SSH key for DistributedProcessProxy set to: {c.DistributedProcessProxy.ssh_key_filename}")