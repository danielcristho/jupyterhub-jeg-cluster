# syntax=docker/dockerfile:1.3

FROM jupyter/base-notebook:latest

USER root

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl net-tools tini && \
    rm -rf /var/lib/apt/lists/*

# FIX: Upgrade JupyterHub to match hub version (5.3.0)
RUN pip install --upgrade jupyterhub==5.3.0

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Create Jupyter config directory
RUN mkdir -p /opt/conda/etc/jupyter

# CRITICAL: Add Jupyter server configuration to force bind to 0.0.0.0
RUN echo "c.ServerApp.ip = '0.0.0.0'" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.port = 8888" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.allow_origin = '*'" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.disable_check_xsrf = True" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.allow_remote_access = True" >> /opt/conda/etc/jupyter/jupyter_server_config.py

# Also add config for JupyterHub SingleUser
RUN echo "c.SingleUserNotebookApp.ip = '0.0.0.0'" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.SingleUserNotebookApp.port = 8888" >> /opt/conda/etc/jupyter/jupyter_server_config.py

# Create user-level config as backup
RUN mkdir -p /home/jovyan/.jupyter && \
    echo "c.ServerApp.ip = '0.0.0.0'" >> /home/jovyan/.jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.port = 8888" >> /home/jovyan/.jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.allow_origin = '*'" >> /home/jovyan/.jupyter/jupyter_server_config.py && \
    chown -R jovyan:users /home/jovyan/.jupyter

# Optional: Ray autoconnect startup (if you're using Ray)
# COPY 00-ray-init.py /usr/local/share/jupyter/startup/00-ray-init.py

USER ${NB_UID}

WORKDIR /home/jovyan

EXPOSE 8888

ENTRYPOINT ["tini", "--"]
CMD ["start-singleuser.sh"]# syntax=docker/dockerfile:1.3

FROM jupyter/base-notebook:latest

USER root

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl net-tools tini && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Create Jupyter config directory
RUN mkdir -p /opt/conda/etc/jupyter

# Add Jupyter server configuration to force bind to 0.0.0.0
RUN echo "c.ServerApp.ip = '0.0.0.0'" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.port = 8888" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.allow_origin = '*'" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.disable_check_xsrf = True" >> /opt/conda/etc/jupyter/jupyter_server_config.py

# Also create config for notebook (legacy support)
RUN echo "c.NotebookApp.ip = '0.0.0.0'" >> /opt/conda/etc/jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.port = 8888" >> /opt/conda/etc/jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_origin = '*'" >> /opt/conda/etc/jupyter/jupyter_notebook_config.py

# Optional: Ray autoconnect startup (if you're using Ray)
# COPY 00-ray-init.py /usr/local/share/jupyter/startup/00-ray-init.py

USER ${NB_UID}

WORKDIR /home/jovyan

EXPOSE 8888

ENTRYPOINT ["tini", "--"]
CMD ["start-singleuser.sh"]