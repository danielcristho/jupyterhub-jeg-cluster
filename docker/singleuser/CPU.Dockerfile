# syntax=docker/dockerfile:1.3

FROM jupyter/base-notebook:latest

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl net-tools tini && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Create Jupyter config directory
RUN mkdir -p /opt/conda/etc/jupyter

RUN echo "c.ServerApp.ip = '0.0.0.0'" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.port = 8888" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.allow_origin = '*'" >> /opt/conda/etc/jupyter/jupyter_server_config.py && \
    echo "c.ServerApp.disable_check_xsrf = True" >> /opt/conda/etc/jupyter/jupyter_server_config.py

RUN echo "c.NotebookApp.ip = '0.0.0.0'" >> /opt/conda/etc/jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.port = 8888" >> /opt/conda/etc/jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_origin = '*'" >> /opt/conda/etc/jupyter/jupyter_notebook_config.py

# COPY 00-ray-init.py /usr/local/share/jupyter/startup/00-ray-init.py

USER ${NB_UID}

WORKDIR /home/jovyan

EXPOSE 8888

ENTRYPOINT ["tini", "--"]
CMD ["start-singleuser.sh"]