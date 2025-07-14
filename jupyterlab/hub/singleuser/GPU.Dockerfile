FROM nvidia/cuda:12.0.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NB_USER=jovyan \
    NB_UID=1000 \
    HOME=/home/jovyan \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Create user
RUN adduser \
    --disabled-password \
    --gecos "Default user" \
    --uid ${NB_UID} \
    --home ${HOME} \
    --force-badname \
    ${NB_USER}

# Install deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-dev python3.10-venv git curl wget tini iputils-ping \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Install JupyterLab and required tools
# RUN pip install --no-cache-dir jupyterlab notebook jupyterhub jupyter-server

# Install other Python packages
COPY GPU.requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY launch_ipykernel.py /usr/local/bin/launch_ipykernel.py

RUN mkdir -p ${HOME}/work

RUN mkdir -p ${HOME}/.jupyter

# # Install GPU-accelerated PyTorch stack
# RUN pip install --no-cache-dir \
#     torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu120

# # Install GPU-accelerated PyTorch stack (cu120, Python 3.10)
# RUN pip install --no-cache-dir \
#     torch==2.2.1 \
#     torchvision==0.17.1 \
#     torchaudio==2.2.1

# Set permissions
RUN chown -R ${NB_USER}:${NB_USER} ${HOME}

USER ${NB_USER}
WORKDIR ${HOME}/work

EXPOSE 8888

ENTRYPOINT ["tini", "--"]

CMD ["jupyterhub-singleuser"]
