# jeg_config.py yang disederhanakan
import os

c = get_config()

# c.EnterpriseGatewayApp.kernel_spec_dirs = ['/usr/local/share/jupyter/kernels']

c.BaseProcessProxy.response_address = '0.0.0.0:8877'

c.EnterpriseGatewayApp.remote_hosts = ['10.21.73.139']

c.MappingKernelManager.cull_idle_timeout = 3600 

c.MappingKernelManager.cull_interval = 300      

c.RemoteProcessProxy.socket_timeout = 5.0

c.RemoteProcessProxy.prepare_timeout = 60.0

# c.EnterpriseGatewayApp.remote_hosts = ['10.33.17.30', '10.21.73.107', '10.21.73.139', '10.21.73.125']

# c.EnterpriseGatewayApp.load_balancing_algorithm="round-robin"

# c.DistributedProcessProxy.ssh_key_filename = '/home/jovyan/.ssh/id_rsa'

c.RemoteProcessProxy.port_range = "40000..50000"

c.DistributedProcessProxy.disable_host_key_checking = True

c.Application.log_format = '[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s] %(message)s'

print("[INFO] JEG config loaded successfully. Using simplified configuration.")
print(f"[INFO] Default SSH key for DistributedProcessProxy set to: {c.DistributedProcessProxy.ssh_key_filename}")