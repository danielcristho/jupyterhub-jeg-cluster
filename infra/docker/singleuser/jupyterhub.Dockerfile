# syntax=docker/dockerfile:1.3
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    NB_USER=jovyan \
    NB_UID=1000 \
    HOME=/home/jovyan \
    RAY_ADDRESS=ray://10.21.73.122:10001

RUN adduser --disabled-password --gecos "Default user" --uid $NB_UID --home $HOME $NB_USER

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Install JupyterLab and Ray
COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY 00-ray-init.py /usr/local/share/jupyter/startup/00-ray-init.py

COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py

EXPOSE 8000
CMD ["jupyterhub"]
