#!/bin/bash
set -e

echo "Starting Enterprise Gateway..."

echo "Starting Jupyter Enterprise Gateway process..."
exec jupyter enterprisegateway --config=/etc/jupyter/jeg_config.py