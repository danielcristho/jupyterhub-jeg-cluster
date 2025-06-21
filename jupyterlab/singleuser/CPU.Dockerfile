FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    NB_USER=jovyan \
    NB_UID=1000 \
    NB_GID=100 \
    HOME=/home/jovyan

# Create user
RUN groupadd --gid ${NB_GID} ${NB_USER} && \
    adduser \
    --disabled-password \
    --gecos "Default user" \
    --uid ${NB_UID} \
    --gid ${NB_GID} \
    --home ${HOME} \
    --force-badname \
    ${NB_USER}

# Install tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git tini curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /tmp/requirements.txt
RUN test -s /tmp/requirements.txt && pip install --no-cache-dir -r /tmp/requirements.txt || true

# Cleanup default Jupyter config
RUN find /opt/conda -name "*jupyter*config*" -type f -delete 2>/dev/null || true && \
    find /usr/local -name "*jupyter*config*" -type f -delete 2>/dev/null || true && \
    find /etc -name "*jupyter*config*" -type f -delete 2>/dev/null || true

# Add permission fixer script
COPY fix-permission.sh /usr/local/bin/fix-permission.sh
RUN chmod +x /usr/local/bin/fix-permission.sh

USER ${NB_USER}
WORKDIR ${HOME}

EXPOSE 8888
VOLUME /home/jovyan/work

ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "/usr/local/bin/fix-permission.sh && exec jupyterhub-singleuser --ip=0.0.0.0 --port=8888 --NotebookApp.default_url=/lab"]
