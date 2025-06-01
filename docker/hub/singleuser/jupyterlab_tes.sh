docker run --rm -p 8888:8888 \
  -e JUPYTERHUB_USER=admin \
  -e JUPYTERHUB_API_URL=http://10.21.73.116:18000/hub/api \
  -e JUPYTERHUB_SERVICE_URL=http://10.21.73.116:18000 \
  danielcristh0/jupyterlab:cpu


docker run --rm -p 8888:8888 \
  -e JUPYTERHUB_USER=test \
  -e JUPYTERHUB_API_URL=http://10.21.73.116:18000/hub/api \
  -e JUPYTERHUB_SERVICE_URL=http://10.21.73.116:18000 \
  danielcristh0/jupyterlab:cpu \
    jupyterhub-singleuser --ip=0.0.0.0 --port=8888 --allow-root
