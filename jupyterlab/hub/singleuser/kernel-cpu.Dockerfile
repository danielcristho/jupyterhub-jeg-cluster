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

RUN apt-get update && apt-get install -y --no-install-recommends \
    git tini curl iputils-ping \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY CPU.requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN mkdir -p ${HOME}/work

RUN mkdir -p ${HOME}/.jupyter

COPY jupyter_server_config.py ${HOME}/.jupyter/jupyter_server_config.py

COPY launch_ipykernel.py /usr/local/bin/launch_ipykernel.py

# Set permissions
RUN chown -R ${NB_USER}:${NB_USER} ${HOME}

USER ${NB_USER}
WORKDIR ${HOME}/work

# EXPOSE 8888

# ENTRYPOINT ["tini", "--"]
# CMD ["jupyterhub-singleuser"]