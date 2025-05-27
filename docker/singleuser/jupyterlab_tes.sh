docker run --rm -p 8888:8888 \
  -e JUPYTERHUB_USER=admin \
  -e JUPYTERHUB_API_URL=http://192.168.122.1:18000/hub/api \
  -e JUPYTERHUB_SERVICE_URL=http://192.168.122.1:18000 \
  danielcristh0/jupyterlab:cpu


docker run --rm -p 8888:8888 \
  -e JUPYTERHUB_USER=admin \
  -e JUPYTERHUB_API_URL=http://192.168.122.1:18000/hub/api \
  -e JUPYTERHUB_SERVICE_URL=http://192.168.122.1:18000 \
  danielcristh0/jupyterlab:cpu