#!/bin/bash
set -ex

REMOTE_IP=${EG_REMOTE_IP:-$(hostname -i)}

docker run --rm -i \
  --network=host \
  -v "{connection_file}":/tmp/kernel.json \
  -e KERNEL_ID="{kernel_id}" \
  -e KERNEL_USERNAME="{kernel_username}" \
  danielcristh0/jupyterlab:cpu \
  python3 -m ipykernel_launcher -f /tmp/kernel.json