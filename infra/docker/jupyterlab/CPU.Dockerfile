# syntax=docker/dockerfile:1.3

FROM python:3.10.14-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    NB_USER=jovyan \
    NB_UID=1000 \
    HOME=/home/jovyan \
    RAY_ADDRESS=ray://10.21.73.122:10001

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
    git tini curl && \
    rm -rf /var/lib/apt/lists/*

# Install JupyterLab and Ray
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

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
CMD ["start-notebook.sh"]