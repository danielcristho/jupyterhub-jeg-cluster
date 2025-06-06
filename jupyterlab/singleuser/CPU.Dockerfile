# syntax=docker/dockerfile:1.3

FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    NB_USER=jovyan \
    NB_UID=1000 \
    HOME=/home/jovyan

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

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN find /opt/conda -name "*jupyter*config*" -type f -delete 2>/dev/null || true && \
    find /usr/local -name "*jupyter*config*" -type f -delete 2>/dev/null || true && \
    find /etc -name "*jupyter*config*" -type f -delete 2>/dev/null || true && \
    rm -rf /opt/conda/etc/jupyter* /usr/local/etc/jupyter* /etc/jupyter* || true

# Add Ray autoconnect script
COPY 00-ray-init.py /usr/local/share/jupyter/startup/00-ray-init.py

# Set up IPython startup
RUN mkdir -p ${HOME}/.ipython/profile_default/startup && \
    cp /usr/local/share/jupyter/startup/00-ray-init.py ${HOME}/.ipython/profile_default/startup/

# Set permissions
RUN chown -R ${NB_USER}:${NB_USER} ${HOME}
RUN rm -rf /home/jovyan/.jupyter* || true


USER ${NB_USER}

WORKDIR ${HOME}

EXPOSE 8888
ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "JUPYTER_CONFIG_DIR=/dev/null JUPYTER_CONFIG_PATH=/dev/null exec jupyterhub-singleuser --ip=0.0.0.0 --port=8888"]