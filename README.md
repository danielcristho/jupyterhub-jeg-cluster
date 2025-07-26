# JupyterHub JEG Cluster

This final project implements a distributed resource management system using Docker containers and JupyterLab. It allows multiple users to access GPU and CPU resources dynamically across multiple nodes through JupyterHub, a custom Discovery API, and Jupyter Enterprise Gateway integration.

JupyterHub serves as the main frontend interface, customized to allow users to select computing profiles and nodes. It integrates with the Discovery Service to choose the most optimal node based on current load and availability, and delegates kernel execution to Jupyter Enterprise Gateway (JEG), which launches kernels on the selected remote nodes.

References:

- [jupyterhub/jupyterhub](https://github.com/jupyterhub/jupyterhub)
- [jupyter-server/enterprise_gateway](https://github.com/jupyter-server/enterprise_gateway)

Demo:

![Demo](demo.gif)

```json
{
  "count": 1,
  "selected_nodes": [
    {
      "active_jupyterlab": 1,
      "active_ray": 0,
      "cpu_cores": 24,
      "cpu_usage_percent": 1.0,
      "created_at": "2025-07-08T20:34:14.203389",
      "disk_usage_percent": 58.5,
      "gpu_info": [],
      "has_gpu": true,
      "hostname": "rpl",
      "id": 201,
      "ip": "10.21.73.139",
      "is_active": true,
      "load_score": 13.28,
      "max_containers": 10,
      "memory_usage_percent": 15.6,
      "ram_gb": 67.11,
      "total_containers": 8,
      "updated_at": "2025-07-10T18:12:15.301315"
    }
  ],
  "status": "ok"
}
```