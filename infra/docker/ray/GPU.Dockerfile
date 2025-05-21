FROM rayproject/ray:2.46.0-py312-gpu

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV TZ=Asia/Jakarta