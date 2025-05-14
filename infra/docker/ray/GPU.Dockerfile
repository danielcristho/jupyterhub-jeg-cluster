FROM rayproject/ray:2.12.0-py310-gpu

ENV TZ=Asia/Jakarta

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN pip install torch==2.3.0+cu118 torchvision==0.18.0+cu118 --extra-index-url https://download.pytorch.org/whl/cu118