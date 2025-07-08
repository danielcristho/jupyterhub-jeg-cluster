# Ambil objek konfigurasi
c = get_config()
c.GatewayClient.gateway_enabled = True

c.Application.log_level = 'INFO'

print("--- jupyter_server_config.py loaded ---")
print("JupyterLab server has been configured to use the Gateway Client.")
print("All kernel operations will be forwarded to Jupyter Enterprise Gateway.")