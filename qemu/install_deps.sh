#!/bin/bash

set -e

DOCKER_VERSION="27.5.1"
DOCKER_BUILD="9f9e405"
DOCKER_TGZ="docker-${DOCKER_VERSION}.tgz"
DOWNLOAD_URL="https://download.docker.com/linux/static/stable/x86_64/${DOCKER_TGZ}"
INSTALL_DIR="/usr/local/bin"

echo "[INFO] Removing old Docker versions (if any)..."
sudo apt-get remove -y docker docker-engine docker.io containerd runc || true

echo "[INFO] Creating temporary directory..."
mkdir -p ~/docker-install
cd ~/docker-install

echo "[INFO] Downloading Docker $DOCKER_VERSION..."
curl -LO $DOWNLOAD_URL

echo "[INFO] Extracting Docker binaries..."
tar xzvf $DOCKER_TGZ

echo "[INFO] Installing Docker binaries to $INSTALL_DIR..."
sudo cp docker/* $INSTALL_DIR

echo "[INFO] Cleaning up..."
cd ~
rm -rf ~/docker-install

echo "[INFO] Verifying Docker version..."
docker --version

echo "[INFO] Installation completed: Docker version ${DOCKER_VERSION}, build ${DOCKER_BUILD}"
