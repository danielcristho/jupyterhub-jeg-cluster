import os

c = get_config()

c.BaseProcessProxy.response_address = '0.0.0.0:8877'

# Cull kernels that have been idle for 1 hour (3600 seconds)
c.MappingKernelManager.cull_idle_timeout = 3600

# Check for idle kernels every 5 minutes (300 seconds)
c.MappingKernelManager.cull_interval = 300

# Timeouts for remote kernel initialization
c.RemoteProcessProxy.socket_timeout = 5.0       # Network socket timeout
c.RemoteProcessProxy.prepare_timeout = 60.0     # Timeout for kernel preparation

# List of allowed remote hosts where kernels can run
c.EnterpriseGatewayApp.remote_hosts = [
    '10.21.73.107',
    '10.21.73.125'
]

# c.EnterpriseGatewayApp.load_balancing_algorithm = "least-connection"

# Kernel containers will use ports within this range
c.RemoteProcessProxy.port_range = "40000..50000"

# Disable SSH host key checking to avoid interactive prompts (used in distributed mode)
c.DistributedProcessProxy.disable_host_key_checking = True

# Optional: specify custom SSH key for launching kernels on remote nodes
# c.DistributedProcessProxy.ssh_key_filename = '/home/jovyan/.ssh/id_rsa'

# Log format for application messages
c.Application.log_format = '[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s] %(message)s'

# Debug output (if ssh_key_filename is enabled)
print(f"[INFO] Default SSH key for DistributedProcessProxy set to: {c.DistributedProcessProxy.ssh_key_filename}")
