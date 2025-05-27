# syntax=docker/dockerfile:1.3
FROM quay.io/jupyter/base-notebook:hub-5.3.0

USER root
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/srv/jupyterhub:$PYTHONPATH

# RUN adduser --disabled-password --gecos "Default Jupyter user" \
#     --uid 1000 \
#      jovyan

RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        curl \
        git \
        ca-certificates \
        libcurl4 \
        libpq5 \
        # nodejs \
        # npm \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
# RUN npm install -g configurable-http-proxy@4.5.1

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip wheel --wheel-dir=/tmp/wheels -r /tmp/requirements.txt \
 && pip install --no-cache-dir --no-index --find-links=/tmp/wheels -r /tmp/requirements.txt

COPY --chown=1000:100 jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
COPY --chown=1000:100 spawner/ /srv/jupyterhub/spawner/
COPY --chown=1000:100 .env /srv/jupyterhub/.env

COPY --chown=1000:100 src /srv/jupyterhub/src

WORKDIR /srv/jupyterhub

EXPOSE 18000

USER 1000

ENTRYPOINT ["tini", "--"]
CMD ["jupyterhub", "--config", "/srv/jupyterhub/jupyterhub_config.py"]
