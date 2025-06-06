FROM nvidia/cuda:12.0.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NB_USER=jovyan \
    NB_UID=1000 \
    HOME=/home/jovyan \
    RAY_ADDRESS=ray://10.21.73.122:10001 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Create user
RUN adduser --disabled-password --gecos "Default user" \
    --uid ${NB_UID} --home ${HOME} --force-badname ${NB_USER}

# Install deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-dev git curl wget tini \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Install JupyterLab and required tools
RUN pip install --no-cache-dir jupyterlab notebook jupyterhub jupyter-server

# Install other Python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# # Install GPU-accelerated PyTorch stack
# RUN pip install --no-cache-dir \
#     torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu120

# Install GPU-accelerated PyTorch stack (cu120, Python 3.10)
RUN pip install --no-cache-dir \
    torch==2.2.1 \
    torchvision==0.17.1 \
    torchaudio==2.2.1

# Add Ray autoconnect script
COPY 00-ray-init.py /usr/local/share/jupyter/startup/00-ray-init.py

# Set up IPython startup
RUN mkdir -p ${HOME}/.ipython/profile_default/startup && \
    cp /usr/local/share/jupyter/startup/00-ray-init.py ${HOME}/.ipython/profile_default/startup/

# Set permissions
RUN chown -R ${NB_USER}:${NB_USER} ${HOME}

USER ${NB_USER}
WORKDIR ${HOME}

EXPOSE 8888
ENTRYPOINT ["tini", "--"]
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--NotebookApp.token=''"]
