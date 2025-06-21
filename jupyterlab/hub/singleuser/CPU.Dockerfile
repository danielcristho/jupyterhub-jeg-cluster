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
    git tini curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN pip install ipykernel && \
    python -m ipykernel install --user --name myenv --display-name "My Custom Python"

# Create working directory for notebooks
RUN mkdir -p ${HOME}/work

RUN mkdir -p ${HOME}/.jupyter

RUN echo "c.ServerApp.ip = '0.0.0.0'" > ${HOME}/.jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.port = 8888" >> ${HOME}/.jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.open_browser = False" >> ${HOME}/.jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.allow_remote_access = True" >> ${HOME}/.jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.token = ''" >> ${HOME}/.jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.password = ''" >> ${HOME}/.jupyter/jupyter_server_config.py

# Set permissions
RUN chown -R ${NB_USER}:${NB_USER} ${HOME}


USER ${NB_USER}
WORKDIR ${HOME}/work

EXPOSE 8888

ENTRYPOINT ["tini", "--"]
CMD ["jupyterhub-singleuser"]